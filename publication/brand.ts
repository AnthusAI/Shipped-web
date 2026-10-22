import type { SiteBrand } from "@anthusai/papyrus/lib/site-brand";
import { DEFAULT_THEME_PACK_TOKENS } from "@anthusai/papyrus/lib/site-stack";

export const shippedBrand: SiteBrand = {
  id: "shipped",
  appTitle: "Shipped",
  appDescription: "Shipped: the AI that actually shipped, checked against their sources and scored.",
  mastheadTitle: "Shipped",
  mastheadSubtitle: "The AI that actually shipped",
  backToHomeLabel: "Back to Shipped",
  articleTitleSuffix: "Shipped",
  placeholderByline: "Shipped",
  defaultPresentation: "blog",
  textFont: '"Inter", system-ui, sans-serif',
  mastheadWordSplit: false,
  mastheadDateFormat: "formatted",
  mastheadSource: "brand",
  sectionLinkStrategy: "route",
  kanbusTheme: "newspaper-gothic",
  themePack: "papyrus",
  themeTokens: DEFAULT_THEME_PACK_TOKENS,
  renderer: { kind: "markus" },
  hosting: { kind: "amplify-ssr" },
  rootRoute: { kind: "redirect", destination: "/newsroom" },
  newsroomBasePath: "/newsroom",
  opsChrome: "app",
  corpusKey: "shipped",
  publicationName: "Shipped",
};
