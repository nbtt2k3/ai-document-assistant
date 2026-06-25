import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pro RAG Chatbot",
  description: "Advanced RAG Chatbot with Document Isolation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        {children}
      </body>
    </html>
  );
}
