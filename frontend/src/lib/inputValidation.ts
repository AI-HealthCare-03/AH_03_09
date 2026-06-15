// 기저질환·알레르기·약물 입력 최소 가드레일

const PROFANITY_LIST = [
  // 기본 욕설
  "씨발", "씨팔", "시발", "시팔", "ㅅㅂ",
  "개새끼", "개년", "개놈",
  "병신", "ㅂㅅ",
  "지랄", "ㅈㄹ",
  "미친놈", "미친년", "미쳤",
  "닥쳐", "꺼져", "죽어",
  // 비하 표현
  "바보", "멍청", "빡대가리", "쓰레기", "찐따", "돌아이",
  // 영어 욕설
  "fuck", "shit", "bitch", "asshole", "bastard", "crap",
];

// 의미있는 문자(한글/영문/숫자)가 최소 1자 이상 포함돼야 함
const MEANINGFUL_RE = /[가-힣a-zA-Z0-9]/;

export function validateHealthInput(value: string): string | null {
  const trimmed = value.trim();

  if (trimmed.length < 2) return "2자 이상 입력해주세요.";

  if (!MEANINGFUL_RE.test(trimmed)) return "올바른 내용을 입력해주세요.";

  const lower = trimmed.toLowerCase();
  if (PROFANITY_LIST.some((w) => lower.includes(w))) {
    return "적절하지 않은 표현이 포함되어 있습니다.";
  }

  return null;
}
