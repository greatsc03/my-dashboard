-- ================================================================
-- 나의 대시보드 — Supabase 테이블 생성 SQL
-- Supabase → SQL Editor 에서 실행하세요
-- ================================================================

CREATE TABLE IF NOT EXISTS quotes (
  id     BIGSERIAL PRIMARY KEY,
  text   TEXT NOT NULL,
  author TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goals (
  id     BIGSERIAL PRIMARY KEY,
  year   TEXT NOT NULL,   -- '2026' or '2030'
  text   TEXT NOT NULL,
  done   BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tasks (
  id      BIGSERIAL PRIMARY KEY,
  day_key TEXT NOT NULL,  -- 'YYYY-MM-DD'
  text    TEXT NOT NULL,
  done    BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS translations (
  id     BIGSERIAL PRIMARY KEY,
  src    TEXT NOT NULL,
  result TEXT NOT NULL,
  mode   TEXT NOT NULL,
  date   TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS settings (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL DEFAULT ''
);

-- 기본 글귀 삽입 (처음 한 번만)
INSERT INTO quotes (text, author) VALUES
  ('오늘 할 수 있는 일에 최선을 다하라. 그러면 내일은 더 잘 할 수 있을 것이다.', 'H. Jackson Brown Jr.'),
  ('The secret of getting ahead is getting started.', 'Mark Twain'),
  ('성공은 최종 목적지가 아니다. 실패는 치명적이지 않다. 계속하는 용기가 중요하다.', 'Winston Churchill'),
  ('In the middle of every difficulty lies opportunity.', 'Albert Einstein'),
  ('자신을 믿어라. 당신은 생각보다 훨씬 용감하고, 보이는 것보다 훨씬 강하다.', 'A.A. Milne')
ON CONFLICT DO NOTHING;
