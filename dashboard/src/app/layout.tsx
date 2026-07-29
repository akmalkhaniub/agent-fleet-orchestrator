import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Agent Fleet Orchestrator - Next.js Control Plane",
  description: "Next.js 16 Web Control & Admin Evaluation Suite for Multi-Agent Fleets",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" />
      </head>
      <body class="antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
