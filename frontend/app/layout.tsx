import './globals.css'

export const metadata = {
  title: 'Home Assistant',
  description: 'AI-powered smart home control',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}
