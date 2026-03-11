import asyncio
import json

from step3_domain_signoff import run_signoff, validate_verdict, MOCK_DRAFTS, REQUIRED_CODES

DOMAINS = ["admin", "finance", "legal"]


async def main():
    for domain in DOMAINS:
        print(f"\n{'=' * 60}")
        print(f"도메인: {domain.upper()}")
        print("=" * 60)

        verdict = await run_signoff(domain, MOCK_DRAFTS[domain])
        print(json.dumps(verdict, ensure_ascii=False, indent=2))

        try:
            validate_verdict(verdict, domain)
        except AssertionError as e:
            print(f"검증 실패: {e}")


if __name__ == "__main__":
    asyncio.run(main())
