
import { Button } from '../atoms/Button';
export const SocialButton = ({ icon, label }) => (
  <Button>
    <img src={icon} width={20} /> {label}
  </Button>
);
