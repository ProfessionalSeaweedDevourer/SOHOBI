import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';

export function KeyboardShortcuts() {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === '/') {
        e.preventDefault();
        toast.info('단축키: ⌘/Ctrl+H (홈), ⌘/Ctrl+U (사용자 채팅)', { duration: 5000 });
      }

      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case 'h':
            e.preventDefault();
            navigate('/');
            toast.success('홈으로 이동');
            break;
          case 'u':
            if (location.pathname !== '/user') {
              e.preventDefault();
              navigate('/user');
              toast.success('사용자 채팅으로 이동');
            }
            break;

        }
      }

      if (e.key === 'Escape' && location.pathname !== '/') {
        navigate(-1);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate, location]);

  return null;
}

export default KeyboardShortcuts;
