# run_profile.py

from profile_logic import (
    list_user_types,
    get_kb_stats,
    retrieve,
    get_risk_level,
    analyze_ingredient,
    DEFAULT_KB_PATH,
    DEFAULT_CHROMA_DIR,
)

def test_list_user_types():
    print("Testing list_user_types:")
    result = list_user_types()
    print(result)

def test_get_kb_stats():
    print("\nTesting get_kb_stats:")
    stats = get_kb_stats(kb_path=DEFAULT_KB_PATH, chroma_dir=DEFAULT_CHROMA_DIR)
    print(stats)

def test_retrieve_ingredient(user_type, ingredient):
    print(f"\nTesting retrieve_ingredient for {ingredient} and {user_type}:")
    entry = retrieve(user_type_kb_key=user_type, ingredient=ingredient)
    print(entry)

def test_get_risk_level():
    print("\nTesting get_risk_level:")
    score = 45  # Example inference score
    risk_level = get_risk_level(score)
    print(f"Score: {score}, Risk Level: {risk_level}")

def test_analyze_ingredient(user_type, ingredient):
    print(f"\nTesting analyze_ingredient for {ingredient} and {user_type}:")
    result = analyze_ingredient(user_type=user_type, ingredient=ingredient)
    print(result)

def main():
    # Test user types
    test_list_user_types()
    
    # Test get_kb_stats
    test_get_kb_stats()

    # Ask the user to input the ingredient and user type
    user_type = input("\nEnter user type (e.g. Asthma, Diabetes, Newborn, etc.): ").strip()
    ingredient = input("Enter ingredient (e.g. Aspirin): ").strip()

    # Test retrieve_ingredient with user input
    test_retrieve_ingredient(user_type, ingredient)
    
    # Test get_risk_level
    test_get_risk_level()

    # Test analyze_ingredient with user input
    test_analyze_ingredient(user_type, ingredient)

if __name__ == "__main__":
    main()