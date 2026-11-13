import type { Metadata } from "next";
import { Geist, Geist_Mono, Lexend, Noto_Nastaliq_Urdu } from "next/font/google";
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

// Urdu lessons (F5). Arabic-script subset only: English words inside Urdu text fall back to
// the sans font, so they stay easy to read.
const notoNastaliqUrdu = Noto_Nastaliq_Urdu({
  variable: "--font-urdu-family",
  subsets: ["arabic"],
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
      className={`${geistSans.variable} ${geistMono.variable} ${lexend.variable} ${notoNastaliqUrdu.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
