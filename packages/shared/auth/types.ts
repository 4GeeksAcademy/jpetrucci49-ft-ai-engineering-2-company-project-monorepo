export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface ProfilePublic {
  id: number;
  user_id: number;
  name: string;
  phone: string | null;
  address: string | null;
}

export interface AuthMe {
  email: string;
  role: string;
  profile: ProfilePublic;
}

export interface UserRegisterPayload {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  address?: string;
}

export interface ProfileUpdatePayload {
  name?: string;
  phone?: string;
  address?: string;
}

export interface ApiValidationError {
  loc: (string | number)[];
  msg: string;
  type: string;
}
