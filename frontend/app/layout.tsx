import "./globals.css";
export const metadata = {
  title: "DermaInsight AI | Research workspace",
  description: "Transparent biomedical image and healthcare research workflows",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
