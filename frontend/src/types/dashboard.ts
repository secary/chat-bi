export interface DashboardKpis {
  total_sales: number;
  row_count: number;
  min_date: string | null;
  max_date: string | null;
  region_count: number;
}

export interface SalesByRegionRow {
  region: string;
  sales_amount: number;
}

export interface SalesByMonthRow {
  month: string;
  sales_amount: number;
}

export interface CustomerByRegionRow {
  region: string;
  active_customers: number;
}

export interface DashboardOverview {
  kpis: DashboardKpis;
  sales_by_region: SalesByRegionRow[];
  sales_by_month: SalesByMonthRow[];
  customer_by_region: CustomerByRegionRow[];
  semantic_counts: Record<string, number>;
  warnings: string[];
}
