"""End-to-end test: Seller Sprite MCP integration through client.py.

直接在容器内测试 RealSellerSpriteClient 的 4 个方法，
验证 MCP 数据是否正确流入 _map_* 映射器并返回标准化格式。
"""
import json
import sys

# Patch rate limiter to no-op for testing
import src.utils.rate_limiter as rl

class _FakeLimiter:
    def acquire_or_raise(self, **kw):
        pass

rl.get_rate_limiter = lambda: _FakeLimiter()

# Force real client
import os
os.environ["SELLER_SPRITE_USE_MOCK"] = "false"

from src.seller_sprite.client import RealSellerSpriteClient

def main():
    client = RealSellerSpriteClient()
    errors = []

    # --- Test 1: get_asin_data ---
    print("=" * 60)
    print("TEST 1: get_asin_data('B08GHW4TBS')")
    try:
        result = client.get_asin_data("B08GHW4TBS")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        assert isinstance(result, dict), "Result should be dict"
        assert result.get("asin") == "B08GHW4TBS", f"ASIN mismatch: {result.get('asin')}"
        assert result.get("title"), "Title should not be empty"
        print("✅ PASS: get_asin_data")
    except Exception as e:
        print(f"❌ FAIL: get_asin_data — {e}")
        errors.append(("get_asin_data", str(e)))

    # --- Test 2: search_keyword ---
    print("\n" + "=" * 60)
    print("TEST 2: search_keyword('dog leash')")
    try:
        result = client.search_keyword("dog leash")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        assert isinstance(result, dict), "Result should be dict"
        assert "keyword" in result, "Should have 'keyword' field"
        assert "search_volume" in result, "Should have 'search_volume' field"
        print("✅ PASS: search_keyword")
    except Exception as e:
        print(f"❌ FAIL: search_keyword — {e}")
        errors.append(("search_keyword", str(e)))

    # --- Test 3: reverse_lookup ---
    print("\n" + "=" * 60)
    print("TEST 3: reverse_lookup('B08GHW4TBS')")
    try:
        result = client.reverse_lookup("B08GHW4TBS")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        assert isinstance(result, dict), "Result should be dict"
        assert "asin" in result, "Should have 'asin' field"
        assert "keywords" in result, "Should have 'keywords' field"
        print("✅ PASS: reverse_lookup")
    except Exception as e:
        print(f"❌ FAIL: reverse_lookup — {e}")
        errors.append(("reverse_lookup", str(e)))

    # --- Test 4: get_category_data ---
    print("\n" + "=" * 60)
    print("TEST 4: get_category_data('pet supplies')")
    try:
        result = client.get_category_data("pet supplies")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        assert isinstance(result, dict), "Result should be dict"
        assert "category" in result, "Should have 'category' field"
        print("✅ PASS: get_category_data")
    except Exception as e:
        print(f"❌ FAIL: get_category_data — {e}")
        errors.append(("get_category_data", str(e)))

    # --- Summary ---
    print("\n" + "=" * 60)
    if errors:
        print(f"SUMMARY: {len(errors)} FAILED:")
        for name, err in errors:
            print(f"  ❌ {name}: {err}")
        sys.exit(1)
    else:
        print("SUMMARY: ALL 4 TESTS PASSED ✅")
        sys.exit(0)

if __name__ == "__main__":
    main()
