import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    const theme = localStorage.getItem('theme');
    if (theme === 'dark' || (!theme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleTheme = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
      setIsDark(true);
    }
  };

  return (
    <button
      onClick={toggleTheme}
      className="relative overflow-hidden w-9 h-9 flex items-center justify-center rounded-lg glass hover:bg-white/10 transition-all"
      aria-label="테마 전환"
    >
      <Sun className={`h-5 w-5 transition-all ${isDark ? 'rotate-90 scale-0 absolute' : 'rotate-0 scale-100'}`} />
      <Moon className={`h-5 w-5 transition-all ${isDark ? 'rotate-0 scale-100' : '-rotate-90 scale-0 absolute'}`} />
    </button>
  );
}

export default ThemeToggle;
