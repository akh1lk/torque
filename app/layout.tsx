import "./globals.css";
import { GeistSans } from "geist/font/sans";
import { Toaster } from "sonner";
import { cn } from "@/lib/utils";

export const metadata = {
  title: "Torque - Turn Videos Into 3D Models",
  description:
    "Upload a short clip. Get an interactive 3D model. No app, no LiDAR required. Powered by Neural Gaussian Splatting.",
  openGraph: {
    images: [
      {
        url: "/og?title=Torque - Turn Videos Into 3D Models",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    images: [
      {
        url: "/og?title=Torque - Turn Videos Into 3D Models",
      },
    ],
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head></head>
      <body 
        className={cn(GeistSans.className, "antialiased")}
        style={{ 
          fontFamily: `-apple-system, BlinkMacSystemFont, ${GeistSans.style.fontFamily}` 
        }}
      >
        <Toaster position="top-center" richColors />
        {children}
      </body>
    </html>
  );
}
