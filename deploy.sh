#!/bin/bash
set -e

echo "=== Building SAM application ==="
sam build

echo ""
echo "=== Deploying SAM stack ==="
sam deploy

echo ""
echo "=== Getting stack outputs ==="
STACK_NAME="digimoncrawler"
FRONTEND_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='FrontendBucketName'].OutputValue" --output text)
DISTRIBUTION_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='DistributionId'].OutputValue" --output text)
CF_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query "Stacks[0].Outputs[?OutputKey=='DistributionUrl'].OutputValue" --output text)

echo ""
echo "=== Uploading frontend ==="
aws s3 sync frontend/ s3://$FRONTEND_BUCKET/ --delete

echo ""
echo "=== Invalidating CloudFront cache ==="
aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" > /dev/null

echo ""
echo "=== Done ==="
echo "URL: $CF_URL"
