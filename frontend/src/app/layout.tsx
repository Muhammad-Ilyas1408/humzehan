import type { Metadata } from "next";
import { Geist, Geist_Mono, Lexend } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// Readability font for the Easy-read learning style.
const lexend = Lexend({
  variable: "--font-lexend-family",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "HumZehan — Study the way your mind works",
  description:
    "Paste a textbook page, choose a learning style, and study it in a format that suits you.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${lexend.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
