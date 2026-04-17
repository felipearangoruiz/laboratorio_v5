import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Laboratorio — Diagnóstico Organizacional",
  description:
    "Entiende cómo funciona realmente tu organización con diagnóstico asistido por IA.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
