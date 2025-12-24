
import { Input } from '../atoms/Input';
import { SocialButton } from '../molecules/SocialButton';

export const UnifiedAuthForm = () => (
  <div>
    <SocialButton icon="/assets/icons/google.svg" label="Continue with Google" />
    <Input placeholder="Email" />
  </div>
);
