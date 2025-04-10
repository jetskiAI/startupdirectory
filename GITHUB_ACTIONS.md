# GitHub Actions for Startup Directory

This document explains how GitHub Actions are used in the Startup Directory project for automated data collection and API deployment.

## What is GitHub Actions?

GitHub Actions is a continuous integration and continuous delivery (CI/CD) platform that allows you to automate your build, test, and deployment pipeline directly from GitHub. It can be used to automate workflows when certain events happen in your repository.

## Workflows in This Project

### 1. Data Collection Workflow

**File**: `.github/workflows/data_collection.yml`

**Purpose**: Automatically collect startup data from accelerator websites on a daily basis.

**Trigger**:

- Runs automatically at midnight UTC daily
- Can be triggered manually from the Actions tab

**What it does**:

- Checks out the repository
- Sets up Python
- Installs dependencies
- Runs the data collection script for each accelerator (YC, Neo, TechStars)

### 2. API Deployment Workflow

**File**: `.github/workflows/deploy_api.yml`

**Purpose**: Deploy the API that serves the startup directory data.

**Trigger**:

- Runs when code is pushed to the main branch
- Can be triggered manually from the Actions tab

**What it does**:

- Checks out the repository
- Sets up Python
- Installs dependencies
- Deploys the API to the hosting provider (placeholder - needs configuration)

## Setup Instructions

### Setting Up Secrets

For the workflows to function correctly, you need to add the following secrets to your GitHub repository:

1. Go to your repository on GitHub
2. Navigate to Settings > Secrets and variables > Actions
3. Click "New repository secret"
4. Add the following secrets:
   - `DATABASE_URL`: Your database connection string
   - `SECRET_KEY`: Your application secret key

### Customizing the Deployment

The deployment workflow (`.github/workflows/deploy_api.yml`) contains placeholder steps that need to be customized for your hosting provider. Common options include:

#### For Heroku:

```yaml
- name: Deploy to Heroku
  uses: akhileshns/heroku-deploy@v3.12.14
  with:
    heroku_api_key: ${{ secrets.HEROKU_API_KEY }}
    heroku_app_name: "your-app-name"
    heroku_email: "your-email@example.com"
```

#### For AWS Elastic Beanstalk:

```yaml
- name: Deploy to AWS Elastic Beanstalk
  uses: einaregilsson/beanstalk-deploy@v20
  with:
    aws_access_key: ${{ secrets.AWS_ACCESS_KEY_ID }}
    aws_secret_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    application_name: your-application-name
    environment_name: your-environment-name
    region: us-west-2
    version_label: ${{ github.sha }}
    deployment_package: deploy.zip
```

## Manual Triggering

To manually trigger a workflow:

1. Go to the "Actions" tab in your repository
2. Select the workflow you want to run
3. Click the "Run workflow" button
4. Select the branch and click "Run workflow"

## Viewing Workflow Results

After a workflow runs, you can see the results in the Actions tab. Each run will show:

- Whether it succeeded or failed
- Logs for each step
- Duration and other details
