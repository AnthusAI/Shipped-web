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
    plugins: [
      {
        name: "newsletter",
        siteId: "shipped",
        siteOrigin: "https://shipped.anth.us",
        computeRoleArn: "arn:aws:iam::712236451410:role/amplify-app-shell-shipped-AmplifyComputeRoleD988057-XMW5ARboawnW",
        sendingDomain: "shipped.anth.us",
        fromAddress: "newsletter@shipped.anth.us",
        fromName: "Shipped",
        instantAlerts: false,
        itemUrlStyle: "directory",
        theme: {
          accent: "#1A1615",
          text: "#1A1615",
          background: "#F5F1EA",
          surface: "#FFFFFF",
          muted: "#5E5752",
          fontFamily: "Archivo, Arial, Helvetica, sans-serif",
          headerBand: "#C6F432",
          headerText: "#1A1615",
          buttonFill: "#C6F432",
          buttonText: "#1A1615",
          buttonBorder: "#1A1615",
          footerBand: "#C6F432",
          footerText: "#1A1615",
          wordmarkImageUrl: "https://shipped.anth.us/assets/email/shipped-wordmark-2x.png",
          wordmarkAlt: "Shipped",
          wordmarkWidth: 268,
          wordmarkHeight: 38,
          footerWordmarkWidth: 140,
          labelFont: "'JetBrains Mono', 'Courier New', monospace",
        },
        lists: [
          {
            id: "weekly",
            name: "The Weekly",
            description: "One email on Fridays: what moved on the map, concepts born this week, and what's new in the wild.",
            kind: "roundup",
            schedule: { draft: "cron(0 13 ? * FRI *)", timezone: "America/New_York" },
            issueType: "newsletter_issue",
            archivePath: "/roundup/",
          },
          {
            id: "alerts-shipped",
            name: "Alerts: In use",
            description: "A short email when something is added to the In use section.",
            kind: "alert",
            rule: { sections: ["shipped"] },
            approval: "admin",
          },
          {
            id: "alerts-open-weights",
            name: "Alerts: Open weights",
            description: "A short email when an open-weights release is added.",
            kind: "alert",
            rule: { sections: ["open-weights"] },
            approval: "admin",
          },
          {
            id: "alerts-decisions",
            name: "Alerts: Decisions in the wild",
            description: "A short email when a decision-model deployment is added.",
            kind: "alert",
            rule: { sections: ["decisions"] },
            approval: "admin",
          },
        ],
      },
      {
        name: "reader-steering",
        computeRoleArn: "arn:aws:iam::712236451410:role/amplify-app-shell-shipped-AmplifyComputeRoleD988057-XMW5ARboawnW",
        dimensions: ["useful", "ready", "advances", "open"],
        snapshot: { schedule: true, intervalHours: 6 },
        ranking: { combination: "shrinkage", shrinkageK: 20, readerShareCap: 0.4, newAccountWeight: 1 / 3, risingMinimumAccountHours: 24 },
        retirementPoll: true,
        reservedConcurrency: 10,
        moderation: { mode: "human" },
        subjects: { types: ["item", "submission", "story", "proposal"] },
        proposals: { publish: true },
      },
    ],
    features: {
      consoleResponder: false,
      inboundEmail: false,
      slack: false,
      storageBackups: false,
    },
  },
});
