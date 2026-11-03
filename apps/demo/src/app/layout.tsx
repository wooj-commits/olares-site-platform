import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Olares Demo",
  description: "Native Olares platform demo — auth, Postgres, MinIO",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <main className="shell">{children}</main>
      </body>
    </html>
  );
}
