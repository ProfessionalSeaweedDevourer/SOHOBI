import { Toaster as Sonner } from "sonner";

const Toaster = ({ ...props }) => {
  const isDark = typeof document !== "undefined" && document.documentElement.classList.contains("dark");
  return (
    <Sonner
      theme={isDark ? "dark" : "light"}
      className="toaster group"
      style={{
        "--normal-bg": "var(--popover)",
        "--normal-text": "var(--popover-foreground)",
        "--normal-border": "var(--border)",
      }}
      {...props}
    />
  );
};

export { Toaster };
