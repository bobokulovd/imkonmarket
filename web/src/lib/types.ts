export type Lang = "uz" | "uz_cyrl" | "uz_new" | "ru" | "kaa" | "en";
export type I18n = Partial<Record<Lang, string>>;

export interface Category { id: number; slug: string; icon: string; name: I18n; count: number; ikpu_default?: string; ikpu_name?: string }
export interface SellerShort { id: number; code: string; name: I18n; region: string; region_i18n: I18n; district_i18n: I18n }
export interface Seller extends SellerShort {
  description: I18n; phone: string; email: string; logo: string | null; product_count: number; inn: string;
}
export interface Product {
  id: number; sku: string; name: I18n; spec: I18n; unit: string; price: string | null; available: number | null;
  category: string; seller: SellerShort; delivery: boolean; image: string | null; image_is_sample?: boolean; min_order: number;
  lead_days: number; sold: number; address: I18n;
  description?: I18n; daily_capacity?: number | null; views?: number;
  stock?: number | null; reserved?: number;
  has_variants?: boolean; brand?: string;
}

// ---- Katalog v2: galereya, variantlar, xususiyatlar
export type AttrType = "text" | "number" | "enum" | "bool";
export type AttrValue = string | number | boolean | (string | number)[];
export interface AttrOption { v: string; name: I18n }
export interface AttributeDef {
  id: number; category: string; code: string; name: I18n; hint: I18n; type: AttrType; unit: string;
  required: boolean; multi: boolean; variant: boolean; options: AttrOption[]; order: number;
}
export interface GalleryImage {
  id: number; url: string; order: number; is_sample: boolean; width: number; height: number;
  bg_ok?: boolean | null; quality?: { bg_ok?: boolean; bg?: "white" | "light" | "color" | "busy"; fill?: number; warnings?: string[] };
}
export interface PublicVariant {
  id: number; sku: string; attributes: Record<string, string | number>; label: I18n; price: string | null;
  available: number | null; image: number | null; image_url: string | null;
}
export interface SellerVariant extends PublicVariant {
  barcode: string; own_price: string | null; stock: number | null; reserved: number; sold: number; is_active: boolean; order: number;
}
export interface VariantAxis { code: string; name: I18n; options: AttrOption[] }
export interface Characteristic { code: string; name: I18n; value: I18n }

export interface ProductDetail extends Product {
  similar: Product[]; same_seller: Product[]; seller_full: Seller;
  images: GalleryImage[]; variants: PublicVariant[]; variant_axes: VariantAxis[]; characteristics: Characteristic[];
  country: string; ikpu: string; weight_kg: string | null; length_cm: string | null; width_cm: string | null; height_cm: string | null;
}
export interface Meta {
  brand: string;
  languages: { code: Lang; label: string }[];
  categories: Category[];
  regions: { key: string; name: I18n }[];
  units: Record<string, I18n>;
  sellers: Seller[];
  stats: { products: number; sellers: number; sellers_total: number; regions: number };
  payments: Record<"click" | "payme" | "bank", { demo: boolean }>;
}
export interface Paged<T> { count: number; next: string | null; previous: string | null; results: T[]; facets?: Facets }
export interface Facets { categories: Record<string, number>; regions: Record<string, number>; sellers: Record<string, number> }

export interface Item {
  id: number; product_id: number; variant_id?: number | null; sku: string; name: I18n; spec: I18n; unit: string; qty: number;
  price: string | null; amount: string; available: number | null;
}
export interface Payment { id: number; method: string; amount: string; status: string; is_demo: boolean; document_no: string; note: string; created_at: string; paid_at: string | null }
export interface ContractShort {
  id: number; number: string; token: string; status: string; date: string; total: string; delivery_cost: string;
  grand_total: string; paid_amount: string; due_amount: string; payment_method: string; buyer_type: string;
  lang: Lang; pdf_url: string; prepayment_percent: number; payment_days: number; delivery_days: number;
  shipped_at: string | null; payments?: Payment[];
}
export interface Log { status: string; text: string; created_at: string }
export interface Order {
  number: string; token: string; seller: Seller; agent: SellerShort | null; buyer_type: string; buyer_name: string;
  buyer_phone: string; payment_method: string; delivery_required: boolean; delivery_address: string; status: string;
  total: string; has_unpriced: boolean; items: Item[]; contract: ContractShort | null; logs: Log[];
  seller_comment: string; created_at: string; lang: Lang;
}
export interface SellerApplication extends Omit<Order, "seller" | "contract"> {
  id: number; seller: SellerShort; contract: ContractShort | null; items_count: number;
  buyer_inn: string; buyer_pinfl: string; buyer_passport: string; buyer_director: string; buyer_email: string;
  buyer_address: string; buyer_bank_name: string; buyer_bank_account: string; buyer_bank_mfo: string; comment: string;
}
export interface Contract extends ContractShort {
  seller: SellerShort; agent: SellerShort | null; payments: Payment[]; created_at: string;
  application: { id: number; number: string; token: string; buyer_name: string; buyer_phone: string; buyer_inn: string;
    buyer_pinfl: string; delivery_required: boolean; delivery_address: string; items: Item[] };
}
export interface SellerProfile {
  id: number; code: string; role: "seller" | "operator"; name: I18n; full_name: string; inn: string; region: string;
  region_i18n: I18n; district_i18n: I18n; address: string; phone: string; email: string; director: string;
  bank_name: string; bank_account: string; bank_mfo: string; treasury_account: string; description: I18n; logo: string | null;
}
export interface SellerProduct extends Product {
  stock: number | null; reserved: number; daily_capacity: number | null; note: string; is_active: boolean;
  image_url: string | null; description: I18n; views: number; updated_at: string;
  brand: string; country: string; ikpu: string; ikpu_name: string; ikpu_confirmed: boolean; barcode: string;
  weight_kg: string | null; length_cm: string | null; width_cm: string | null; height_cm: string | null;
  attributes: Record<string, AttrValue>; has_variants: boolean; images: GalleryImage[]; variants: SellerVariant[];
}
export interface IkpuItem { code: string; name: string; group: string; class: string; position: string; subposition: string; brand: string }
export interface Readiness {
  score: number;
  checks: { key: string; ok: boolean; label: string; weight: number }[];
  marketplaces: { account: number; marketplace: "uzum" | "ozon" | "yandex" | "wb"; name: string; status: string; can_create: boolean;
    ok: boolean; errors: string[]; listings: { id: number; offer_id: string; status: string; error: string }[] }[];
}
