import { Toaster } from 'sonner';

export function ToastProvider() {
  const isDark =
    typeof document !== 'undefined' &&
    document.documentElement.classList.contains('dark');

  return (
    <Toaster
      theme={isDark ? 'dark' : 'light'}
      position="top-right"
      toastOptions={{
        style: {
          background: 'var(--glass-bg)',
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          border: '1px solid var(--glass-border)',
          color: 'var(--foreground)',
        },
      }}
      richColors
    />
  );
}

export default ToastProvider;
