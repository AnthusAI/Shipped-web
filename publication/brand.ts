import type { SiteBrand } from "@anthusai/papyrus/lib/site-brand";
import { DEFAULT_THEME_PACK_TOKENS } from "@anthusai/papyrus/lib/site-stack";

export const shippedBrand: SiteBrand = {
  id: "shipped",
  appTitle: "Shipped",
  appDescription: "Shipped: new arrivals in machine learning.",
  mastheadTitle: "Shipped",
  mastheadSubtitle: "New arrivals in machine learning.",
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
  rootRoute: { kind: "newsroom" },
  newsroomBasePath: "",
  opsChrome: "app",
  corpusKey: "shipped",
  publicationName: "Shipped",
};
