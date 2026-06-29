import { Inter } from "next/font/google";
import "./globals.css";
import { Sidebar, Navbar } from "@/components/layout";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "IPL Analytics Platform",
  description: "Next-generation analytics for the Indian Premier League.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} antialiased min-h-screen flex`}>
        <Sidebar />
        
        <div className="flex-1 md:ml-64 flex flex-col min-h-screen">
          <Navbar />
          <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
