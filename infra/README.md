# Shipped infrastructure

`site.json` configures the Papyrus Amplify app-shell stack (the CMS app) for this publication. `package.json` pins `@anthusai/papyrus`, which supplies the template.

```bash
npm ci
npx papyrus-infra synth --site site.json
```

Synthesis only prints and writes `cdk.out/`. Deploying is a separate, reviewed step.

## One edge for the site and the newsroom

The public site is the S3 projection that the CMS backend creates (`backend.publication` in `../papyrus.config.ts`). `site.json` has no `reader` and no domain, so the stack creates only the CMS app (`shipped-cms`).

`edge/shipped.yaml` is the CloudFormation stack `papyrus-edge-shipped`: one CloudFront distribution for `shipped.anth.us`. The default behavior serves the site bucket through origin access control; `/newsroom*`, `/_next/*` and `/api/*` go to the CMS app's `main` branch uncached, with the viewer's host in `x-forwarded-host`.

The distribution has no `CustomErrorResponses`: those apply to every behavior and would replace the CMS `/api/*` errors (a same-origin 403, the reader API) with the 404 page. The default behavior has a Lambda@Edge origin-response function instead that serves the site's `404.html` with status 404 for an S3 miss (see Papyrus `infra/edge/README.md`). Change the function code and the `NotFoundPageVersion` description together.

Order, because the edge needs the bucket and the redirects store the backend creates, and the backend needs the real distribution ARN:

1. Deploy the backend once without `edgeDistributionArn` (first `main` build).
2. Create the edge stack with a change set: `SiteBucketRegionalDomainName`, `SiteViewerRequestFunctionArn` (the backend stack's `RedirectAndIndexFunction`, which carries the redirects store and Markdown negotiation), `CmsAppId` and `CertificateArn` once the ACM certificate is issued.
3. Set `edgeDistributionArn` in `../papyrus.config.ts` to the stack's `DistributionArn` and merge.
4. Point the `shipped` record in the `anth.us` zone at the distribution.

## The console host

The newsroom console is moving to `newsroom.shipped.anth.us` (decided 2026-10-31), like `newsroom.anth.us`. `edge/shipped-console.yaml` is its own CloudFormation stack, `papyrus-edge-shipped-console`, in us-east-1:

- one CloudFront distribution with the alias `newsroom.shipped.anth.us` whose only origin is the CMS app's `main` branch, uncached, with every method and the viewer's host in `x-forwarded-host`. Every path (`/newsroom*`, `/_next/*`, `/api/*`, `/cli/*`, `/.well-known/papyrus-cli.json`) reaches the CMS app;
- its own ACM certificate, validated by a DNS record that ACM writes into the `anth.us` hosted zone (`HostedZoneId`, the zone in the account that deploys the stack), and the A and AAAA alias records in the same zone;
- no S3 origin and no `CustomErrorResponses`, so the CMS answers its own errors.

It does not use an Amplify domain association: `create-domain-association` is throttled in the papyrus-production account.

Create it with a change set, read the change set, then execute it (parameters only; the zone id and the app id are not stored in this repository):

```bash
export AWS_PROFILE=papyrus-production AWS_REGION=us-east-1
aws cloudformation create-change-set --stack-name papyrus-edge-shipped-console --change-set-name create-console --change-set-type CREATE --template-body file://infra/edge/shipped-console.yaml --parameters ParameterKey=HostedZoneId,ParameterValue=<anth.us zone id> ParameterKey=CmsAppId,ParameterValue=<CmsAppId output of amplify-app-shell-shipped-cms>
aws cloudformation describe-change-set --stack-name papyrus-edge-shipped-console --change-set-name create-console
aws cloudformation execute-change-set --stack-name papyrus-edge-shipped-console --change-set-name create-console
```

Expected change set: one certificate, one CloudFront function, one distribution and two record sets, all additions. The stack waits for the certificate to validate, so it takes a few minutes. The public edge stack (`papyrus-edge-shipped`) is not touched until the console has been verified on the new host.

Never connect the repository from the Amplify console on an app that already has branches.
