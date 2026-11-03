import "./globals.css";

export const metadata = {
  title: "Question Paper Analyzer",
  description: "Historical examination pattern analysis and semantic question search."
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
