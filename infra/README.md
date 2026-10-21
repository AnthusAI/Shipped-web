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

Order, because the edge needs the bucket and the redirects store the backend creates, and the backend needs the real distribution ARN:

1. Deploy the backend once without `edgeDistributionArn` (first `main` build).
2. Create the edge stack with a change set: `SiteBucketRegionalDomainName`, `RedirectsKeyValueStoreArn`, `CmsAppId` and `CertificateArn` once the ACM certificate is issued.
3. Set `edgeDistributionArn` in `../papyrus.config.ts` to the stack's `DistributionArn` and merge.
4. Point the `shipped` record in the `anth.us` zone at the distribution.

Never connect the repository from the Amplify console on an app that already has branches.
