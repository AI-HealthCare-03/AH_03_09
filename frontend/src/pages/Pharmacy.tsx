import { ClockIcon, MapPinIcon, PhoneIcon, SearchIcon } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

type StockStatus = "available" | "limited" | "unavailable";

interface Pharmacy {
  id: string;
  name: string;
  address: string;
  distanceM: number;
  phone: string;
  hours: string;
  isOpen: boolean;
}

const PHARMACIES: Pharmacy[] = [
  { id: "1", name: "건강약국", address: "서울시 강남구 테헤란로 123", distanceM: 230, phone: "02-1111-2222", hours: "09:00~22:00", isOpen: true },
  { id: "2", name: "미래약국", address: "서울시 강남구 역삼로 45", distanceM: 450, phone: "02-2222-3333", hours: "09:00~20:00", isOpen: true },
  { id: "3", name: "한솔약국", address: "서울시 강남구 언주로 78", distanceM: 680, phone: "02-3333-4444", hours: "09:00~21:00", isOpen: false },
  { id: "4", name: "연세약국", address: "서울시 강남구 봉은사로 12", distanceM: 920, phone: "02-4444-5555", hours: "08:00~22:00", isOpen: true },
  { id: "5", name: "그린약국", address: "서울시 강남구 삼성로 200", distanceM: 1100, phone: "02-5555-6666", hours: "24시간", isOpen: true },
  { id: "6", name: "행복약국", address: "서울시 강남구 학동로 55", distanceM: 1350, phone: "02-6666-7777", hours: "09:00~19:00", isOpen: false },
  { id: "7", name: "서울중앙약국", address: "서울시 강남구 선릉로 88", distanceM: 1600, phone: "02-7777-8888", hours: "08:30~21:00", isOpen: true },
];

function getStock(pharmacyId: string, query: string): StockStatus {
  const hash = [...(pharmacyId + query.trim().toLowerCase())].reduce(
    (acc, c) => acc + c.charCodeAt(0),
    0,
  );
  const pool: StockStatus[] = ["available", "available", "limited", "unavailable", "available"];
  return pool[hash % pool.length];
}

const STOCK_CONFIG: Record<StockStatus, { label: string; variant: "default" | "secondary" | "destructive" }> = {
  available: { label: "재고 있음", variant: "default" },
  limited: { label: "재고 적음", variant: "secondary" },
  unavailable: { label: "재고 없음", variant: "destructive" },
};

function formatDistance(m: number) {
  return m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${m}m`;
}

export default function Pharmacy() {
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState("");

  const handleSearch = () => {
    const trimmed = query.trim();
    if (!trimmed) return;
    setSearched(trimmed);
  };

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">근처 약국 재고 확인</h1>
        <p className="text-sm text-muted-foreground">
          약 이름을 검색하면 근처 약국의 재고 현황을 확인할 수 있어요.
        </p>
      </header>

      <div className="flex gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="약 이름 검색 (예: 타이레놀, 아스피린)"
          className="flex-1"
        />
        <Button onClick={handleSearch} disabled={!query.trim()}>
          <SearchIcon className="mr-1.5 size-4" />
          검색
        </Button>
      </div>

      {searched ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700">
              <span className="text-primary">"{searched}"</span> 검색 결과 — {PHARMACIES.length}개 약국
            </p>
            <p className="text-xs text-muted-foreground">거리순 정렬</p>
          </div>

          {PHARMACIES.map((p) => {
            const stock = getStock(p.id, searched);
            const stockCfg = STOCK_CONFIG[stock];
            return (
              <Card key={p.id} className="rounded-2xl">
                <CardContent className="flex items-start justify-between gap-4 p-5">
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-900">{p.name}</span>
                      <span
                        className={`text-xs font-medium ${p.isOpen ? "text-emerald-600" : "text-slate-400"}`}
                      >
                        {p.isOpen ? "영업중" : "영업종료"}
                      </span>
                    </div>
                    <div className="space-y-1 text-xs text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <MapPinIcon className="size-3.5 shrink-0" />
                        <span>{p.address}</span>
                        <span className="text-slate-400">({formatDistance(p.distanceM)})</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <ClockIcon className="size-3.5 shrink-0" />
                        <span>{p.hours}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <PhoneIcon className="size-3.5 shrink-0" />
                        <span>{p.phone}</span>
                      </div>
                    </div>
                  </div>
                  <Badge variant={stockCfg.variant} className="shrink-0">
                    {stockCfg.label}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}

          <p className="text-center text-xs text-muted-foreground">
            ⚠️ 재고 정보는 모의 데이터입니다. 방문 전 반드시 전화로 확인하세요.
          </p>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 py-20 text-center">
          <span className="text-4xl">🏥</span>
          <p className="text-sm text-muted-foreground">
            약 이름을 검색하면 근처 약국과 재고 현황이 나타나요.
          </p>
        </div>
      )}
    </div>
  );
}
