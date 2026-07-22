import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Toaster } from "react-hot-toast";
import { AuthProvider } from "./contexts/auth-context";
import { ChatProvider } from "./chat-context";

import "./globals.css";


export const metadata: Metadata = {
    title: "Archimedes",
    description: "Archimedes - Modern AI Assistant Workspace",
};


export default function RootLayout({
    children,
}: Readonly<{
    children: ReactNode;
}>) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body suppressHydrationWarning>
                <AuthProvider>
                    <ChatProvider>
                        {children}
                        <Toaster position="bottom-right" />
                    </ChatProvider>
                </AuthProvider>
            </body>
        </html>
    );
}

