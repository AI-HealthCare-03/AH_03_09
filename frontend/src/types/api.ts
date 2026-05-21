export interface ChatSessionResponse {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatMessageResponse {
  id: number;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export interface ChatMessageListResponse {
  messages: ChatMessageResponse[];
}

export interface SendMessageResponse {
  user_message: ChatMessageResponse;
  assistant_message: ChatMessageResponse;
}

export interface UserInfoResponse {
  id: number;
  kakao_id: string;
  email: string | null;
  name: string | null;
  gender: string | null;
  age_range: string | null;
  birthday: string | null;
  birthyear: string | null;
  phone_number: string | null;
  created_at: string | null;
}
