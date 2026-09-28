import "@fontsource-variable/inter";
import "./globals.css";
import type { Metadata, Viewport } from "next";
import { AppProvider } from "@/lib/store";

export const metadata: Metadata = {
  title: { default: "ImkonMarket — ishlab chiqaruvchidan to'g'ridan-to'g'ri", template: "%s · ImkonMarket" },
  description: "Muassasalar ishlab chiqargan mebel, qurilish materiallari, to'qimachilik va boshqa mahsulotlar. Ariza, shartnoma, Click/Payme/bank orqali to'lov.",
};
export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#1d54f0" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uz">
      <body>
        <AppProvider>{children}</AppProvider>
      </body>
    </html>
  );
}
