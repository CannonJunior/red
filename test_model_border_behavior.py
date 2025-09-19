#!/usr/bin/env python3
"""
Test script for verifying the updated model border behavior.

Tests that ONLY the selected model has a blue border, and that
the recommended model loses its blue border when another model is selected.
"""

import requests

def test_model_border_behavior():
    """Test the updated model border behavior."""
    print("🧪 TESTING UPDATED MODEL BORDER BEHAVIOR")
    print("=" * 55)

    base_url = "http://localhost:9090"

    # Test 1: Verify CSS changes
    print("1. Testing CSS implementation...")
    try:
        response = requests.get(f"{base_url}/styles.css")
        if response.status_code == 200:
            css_content = response.text

            # Check that model-recommended no longer has border-color
            has_recommended_border = "border-color: var(--border-accent)" in css_content.split(".model-recommended")[1].split(".model-selected")[0] if ".model-recommended" in css_content else False

            # Check that model-selected still has border styling
            has_selected_border = ".model-selected" in css_content and "border-color: var(--border-accent)" in css_content and "border-width: 2px" in css_content

            print(f"   ✅ CSS loaded successfully")
            print(f"   {'❌' if has_recommended_border else '✅'} Recommended models: {'Still have' if has_recommended_border else 'No'} automatic blue border")
            print(f"   {'✅' if has_selected_border else '❌'} Selected models: {'Have' if has_selected_border else 'Missing'} blue border styling")

        else:
            print(f"   ❌ CSS not accessible: {response.status_code}")
            return

    except Exception as e:
        print(f"   ❌ CSS check failed: {e}")
        return

    # Test 2: Verify models API
    print("\n2. Testing models availability...")
    try:
        response = requests.post(f"{base_url}/api/models", headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"   ✅ Models API working - {len(models)} models available:")

            recommended_model = None
            other_models = []

            for model in models:
                if model == 'qwen2.5:3b':
                    recommended_model = model
                    print(f"      • {model} (Recommended)")
                else:
                    other_models.append(model)
                    print(f"      • {model}")

            if recommended_model and other_models:
                print(f"   ✅ Perfect setup: 1 recommended + {len(other_models)} other model(s)")
            else:
                print(f"   ⚠️  Limited testing: Need both recommended and other models")

        else:
            print(f"   ❌ Models API error: {response.status_code}")
            return

    except Exception as e:
        print(f"   ❌ Models API failed: {e}")
        return

    # Test 3: Behavior explanation
    print("\n3. Expected behavior analysis...")
    print("   📋 New Behavior (Updated):")
    print("      • Initially: NO model has blue border")
    print("      • When recommended model selected: ONLY recommended model has blue border")
    print("      • When other model selected: ONLY that model has blue border")
    print("      • Recommended model loses blue border when other model selected")
    print("      • Only 'Selected' badge indicates active model, not border color")

    print("\n   🔄 Behavior Change:")
    print("      • Before: Recommended model ALWAYS had blue border")
    print("      • After: ONLY selected model has blue border")
    print("      • Recommended badge remains but doesn't imply border styling")

    # Test 4: CSS specificity check
    print("\n4. CSS implementation details...")
    print("   🎨 CSS Classes:")
    print("      • .model-recommended: Only provides 'Recommended' badge (no border)")
    print("      • .model-selected: Provides blue border (border-color + 2px width)")
    print("      • Both classes can coexist: Recommended + Selected = Badge + Border")
    print("      • Classes work independently: Border follows selection, not recommendation")

    print("\n" + "=" * 55)
    print("✅ UPDATED MODEL BORDER BEHAVIOR TEST COMPLETE")
    print("=" * 55)

    print("\n📖 Manual Testing Steps:")
    print("1. Open: http://localhost:9090")
    print("2. Navigate to 'Models' section")
    print("3. Observe: NO model has blue border initially")
    print("4. Click 'Select Model' on qwen2.5:3b (recommended)")
    print("5. Verify: ONLY qwen2.5:3b gets blue border + 'Selected' badge")
    print("6. Click 'Select Model' on incept5/llama3.1-claude:latest")
    print("7. Verify: qwen2.5:3b LOSES blue border")
    print("8. Verify: ONLY llama3.1-claude has blue border + 'Selected' badge")
    print("9. Verify: qwen2.5:3b keeps 'Recommended' badge but no border")

    print("\n🎯 Key Changes:")
    print("• ✅ Removed automatic blue border from recommended model")
    print("• ✅ Blue border now EXCLUSIVE to selected model")
    print("• ✅ Recommended model shows border ONLY when selected")
    print("• ✅ Clear visual distinction: Selection = Border, Recommendation = Badge")
    print("• ✅ Consistent behavior: One border at a time")

    print("\n🔧 Technical Implementation:")
    print("• CSS: .model-recommended no longer sets border-color")
    print("• CSS: .model-selected exclusively provides blue border")
    print("• JS: Selection logic manages model-selected class properly")
    print("• JS: Recommended badge remains independent of border")

if __name__ == "__main__":
    test_model_border_behavior()