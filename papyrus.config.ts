import { defineSite } from "@anthusai/papyrus/define-site";
import { shippedBrand } from "./publication/brand";

const defaultCognitoDomainPrefix = "papyrus-shipped-cms";
const defaultRedirectUrls = ["http://localhost:3001/", "https://shipped.anth.us/"];

function readNonEmptyEnvironmentValue(name: string): string | undefined {
  const value = process.env[name]?.trim();
  return value ? value : undefined;
}

const cognitoDomainPrefixFromEnvironment = readNonEmptyEnvironmentValue("PAPYRUS_COGNITO_DOMAIN_PREFIX");
const redirectUrlsFromEnvironment = readNonEmptyEnvironmentValue("PAPYRUS_OAUTH_REDIRECT_URLS");

export const resolvedAuthConfiguration = {
  cognitoDomainPrefix: cognitoDomainPrefixFromEnvironment ?? defaultCognitoDomainPrefix,
  applyCognitoDomainPrefix: readNonEmptyEnvironmentValue("PAPYRUS_APPLY_COGNITO_DOMAIN_PREFIX") !== "false",
  disableGoogleOAuth: readNonEmptyEnvironmentValue("PAPYRUS_DISABLE_GOOGLE_OAUTH") === "1",
  redirectUrls: redirectUrlsFromEnvironment
    ? redirectUrlsFromEnvironment.split(",").map((url) => url.trim()).filter((url) => url.length > 0)
    : defaultRedirectUrls,
};

export default defineSite({
  brands: [shippedBrand],
  defaultBrand: "shipped",
  backend: {
    brandId: "shipped",
    auth: resolvedAuthConfiguration,
    publication: {
      kind: "s3-projection",
      staticDir: "web",
      reprojectOnDeploy: true,
      edgeDistributionArn: "arn:aws:cloudfront::712236451410:distribution/EUQZ249T4OKXH",
    },
    stagingBuild: { enabled: false },
    features: {
      consoleResponder: false,
      inboundEmail: false,
      slack: false,
      storageBackups: false,
    },
  },
});
