
import * as SecureStore from 'expo-secure-store';

export const SecureTokenStorage = {
  get: () => SecureStore.getItemAsync('token'),
  set: (t: string) => SecureStore.setItemAsync('token', t),
  clear: () => SecureStore.deleteItemAsync('token')
};
