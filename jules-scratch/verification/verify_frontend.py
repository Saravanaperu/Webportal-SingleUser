from playwright.sync_api import Page, expect

def test_frontend_renders(page: Page):
    """
    This test verifies that the new React frontend renders correctly.
    """
    # 1. Arrange: Go to the React app's URL.
    page.goto("http://localhost:3000")

    # 2. Assert: Check for the main heading.
    expect(page.get_by_role("heading", name="Options Scalping Portal")).to_be_visible()

    # 3. Assert: Check for the section headings.
    expect(page.get_by_role("heading", name="Account Overview")).to_be_visible()
    expect(page.get_by_role("heading", name="Daily Stats")).to_be_visible()
    expect(page.get_by_role("heading", name="Strategy Controls")).to_be_visible()
    expect(page.get_by_role("heading", name="Strategy Parameters")).to_be_visible()
    expect(page.get_by_role("heading", name="Open Positions")).to_be_visible()
    expect(page.get_by_role("heading", name="Historical Trades")).to_be_visible()

    # 4. Screenshot: Capture the final result for visual verification.
    page.screenshot(path="jules-scratch/verification/verification.png")
