export type MurabahaCategory = "consumer" | "phones" | "auto";

export type MurabahaTariffKey =
  | "NO_DOWNPAYMENT"
  | "NO_GUARANTOR"
  | "ONE_GUARANTOR"
  | "TWO_GUARANTORS";

export const MURABAHA_CATEGORY_LABELS: Record<MurabahaCategory, string> = {
  consumer: "Потребительские товары",
  phones: "Телефоны",
  auto: "Автомобили",
};

export const MURABAHA_TARIFF_LABELS: Record<MurabahaTariffKey, string> = {
  NO_DOWNPAYMENT: "Без взноса",
  NO_GUARANTOR: "Без поручителя",
  ONE_GUARANTOR: "С 1 поручителем",
  TWO_GUARANTORS: "С 2 поручителями",
};

export interface MurabahaQuote {
  product_category: string;
  tariff: string;
  principal: string;
  markup: string;
  total: string;
  down_payment_pct: number;
  down_payment_amount: string;
  financed_amount: string;
  monthly_payment: string;
  duration_months: number;
  rate_per_month_pct: string;
}

export interface MurabahaTariffOption {
  key: string;
  label: string;
  enabled: boolean;
  amount_min: number;
  amount_max: number;
}

export interface MurabahaTariffOptions {
  category: string;
  category_label: string;
  terms_min: number;
  terms_max: number;
  special_requirements: string[];
  tariffs: MurabahaTariffOption[];
  default_tariff: string | null;
}
