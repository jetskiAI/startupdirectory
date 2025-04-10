from flask import Blueprint, request, jsonify
from marshmallow import ValidationError
from sqlalchemy import extract

from app.models.db import db
from app.models.startup import Startup, Founder
from app.schemas.startup_schema import StartupSchema, FounderSchema, StartupQuerySchema

# Create Blueprint
startup_bp = Blueprint("startup", __name__)

# Initialize schemas
startup_schema = StartupSchema()
startups_schema = StartupSchema(many=True)
founder_schema = FounderSchema()
query_schema = StartupQuerySchema()


@startup_bp.route("/startups", methods=["GET"])
def get_startups():
    """Get all startups with optional filtering"""
    try:
        # Parse and validate query parameters
        query_params = query_schema.load(request.args)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    # Build the query
    query = Startup.query

    # Apply filters
    if "year" in query_params:
        query = query.filter(Startup.year_founded == query_params["year"])
    if "source" in query_params:
        query = query.filter(Startup.source == query_params["source"])
    if "industry" in query_params:
        query = query.filter(Startup.industry == query_params["industry"])

    # Pagination
    page = query_params.get("page", 1)
    per_page = query_params.get("per_page", 20)

    paginated_startups = query.paginate(page=page, per_page=per_page)

    # Serialize the results
    result = {
        "startups": startups_schema.dump(paginated_startups.items),
        "total": paginated_startups.total,
        "pages": paginated_startups.pages,
        "page": page,
    }

    return jsonify(result), 200


@startup_bp.route("/startups/<int:id>", methods=["GET"])
def get_startup(id):
    """Get a specific startup by ID"""
    startup = Startup.query.get_or_404(id)
    return jsonify(startup_schema.dump(startup)), 200


@startup_bp.route("/startups", methods=["POST"])
def create_startup():
    """Create a new startup"""
    try:
        # Parse and validate request data
        startup_data = startup_schema.load(request.json)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    # Extract founders data if present
    founders_data = request.json.get("founders", [])

    # Create startup
    new_startup = Startup(**startup_data)
    db.session.add(new_startup)

    # Need to flush to get the startup ID for founders
    db.session.flush()

    # Create founders if provided
    for founder_data in founders_data:
        try:
            validated_founder = founder_schema.load(founder_data)
            new_founder = Founder(**validated_founder)
            new_founder.startup_id = new_startup.id
            db.session.add(new_founder)
        except ValidationError as err:
            # If validation fails for a founder, skip it
            continue

    db.session.commit()

    # Return the created startup with its founders
    return jsonify(startup_schema.dump(new_startup)), 201


@startup_bp.route("/startups/<int:id>", methods=["PUT"])
def update_startup(id):
    """Update an existing startup"""
    startup = Startup.query.get_or_404(id)

    try:
        # Parse and validate request data
        startup_data = startup_schema.load(request.json, partial=True)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    # Update startup fields
    for key, value in startup_data.items():
        setattr(startup, key, value)

    db.session.commit()

    return jsonify(startup_schema.dump(startup)), 200


@startup_bp.route("/startups/<int:id>", methods=["DELETE"])
def delete_startup(id):
    """Delete a startup"""
    startup = Startup.query.get_or_404(id)

    db.session.delete(startup)
    db.session.commit()

    return jsonify({"message": f"Startup with id {id} deleted"}), 200


@startup_bp.route("/years", methods=["GET"])
def get_years():
    """Get list of years with startups"""
    years = (
        db.session.query(Startup.year_founded)
        .distinct()
        .order_by(Startup.year_founded.desc())
        .all()
    )
    return jsonify({"years": [year[0] for year in years]}), 200


@startup_bp.route("/years/<int:year>", methods=["GET"])
def get_startups_by_year(year):
    """Get startups for a specific year"""
    try:
        # Parse and validate query parameters
        query_params = query_schema.load(request.args)
    except ValidationError as err:
        return jsonify({"error": err.messages}), 400

    # Build the query
    query = Startup.query.filter(Startup.year_founded == year)

    # Apply additional filters
    if "source" in query_params:
        query = query.filter(Startup.source == query_params["source"])
    if "industry" in query_params:
        query = query.filter(Startup.industry == query_params["industry"])

    # Pagination
    page = query_params.get("page", 1)
    per_page = query_params.get("per_page", 20)

    paginated_startups = query.paginate(page=page, per_page=per_page)

    # Serialize the results
    result = {
        "year": year,
        "startups": startups_schema.dump(paginated_startups.items),
        "total": paginated_startups.total,
        "pages": paginated_startups.pages,
        "page": page,
    }

    return jsonify(result), 200
