"""Browser smoke check for the isolated fictional demo deployment."""

import os
from playwright.sync_api import sync_playwright


BASE = os.environ.get("E2E_BASE_URL", "http://127.0.0.1:8000")
OWNER_PASSWORD = os.environ["DEMO_OWNER_PASSWORD"]
ADMIN_PASSWORD = os.environ["DEMO_ADMIN_PASSWORD"]
EMPLOYEE_PASSWORD = os.environ["DEMO_EMPLOYEE_PASSWORD"]
TAB_IDS = {"Заказы":"orders", "Смены":"schedule", "Зарплата":"payroll", "Долги":"debts"}


def click_tab(page, label):
    page.locator(f'.sidebar button[data-view="{TAB_IDS[label]}"]').click()


def sign_in(page, username, password, heading):
    page.locator('input[name="username"]').fill(username)
    page.locator('input[name="password"]').fill(password)
    page.get_by_role("button", name="Войти").click()
    page.get_by_role("heading", name=heading).wait_for()


def run():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page.on("pageerror", lambda error: print("PAGEERROR:", error))
        page.on("response", lambda response: print("HTTP:", response.status, response.url)
                if response.status >= 400 else None)
        page.goto(BASE)
        page.get_by_text("Демо-версия. Все данные вымышленные").wait_for()

        # Owner: all four tabs, creates a fictional shift and order, then logs out.
        sign_in(page, "demo-owner", OWNER_PASSWORD, "Заказы")
        for tab, heading in (("Заказы", "Заказы"), ("Смены", "Календарь смен и заказов"), ("Зарплата", "Зарплата сотрудников"), ("Долги", "Долги сотрудников")):
            click_tab(page, tab)
            page.get_by_role("heading", name=heading).wait_for()

        people = page.evaluate("fetch('/api/employees').then(r=>r.json())")
        cashier = next(person for person in people if person["name"] == "Азамат")
        hall = next(person for person in people if person["name"] == "Айбек")
        click_tab(page, "Смены")
        page.get_by_role("button", name="＋ Смена").click()
        page.locator('input[name="date"]').fill("2026-11-23")
        page.locator('select[name="shift_type"]').select_option("День")
        page.locator('select[name="cashier_id"]').select_option(str(cashier["id"]))
        page.locator('select[name="hall_id"]').select_option(str(hall["id"]))
        page.locator("#modalBody button[type=submit]").click()
        if page.get_by_role("button", name="Всё равно сохранить").count():
            page.get_by_role("button", name="Всё равно сохранить").click()
        page.get_by_text("Изменения сохранены").wait_for(timeout=8000)

        click_tab(page, "Заказы")
        page.get_by_role("button", name="＋ Новый заказ").click()
        page.locator('input[name="supplier"]').fill("Поставщик E2E")
        page.locator('textarea[name="items_text"]').fill("Вымышленный товар")
        page.locator('input[name="amount"]').fill("12500")
        page.locator("#modalBody button[type=submit]").click()
        page.get_by_text("Поставщик E2E").wait_for(timeout=8000)
        page.get_by_role("button", name="Выйти").click()
        page.locator('input[name="username"]').wait_for()

        # Admin: all four views and logout.
        sign_in(page, "demo-admin", ADMIN_PASSWORD, "Заказы")
        for tab, heading in (("Заказы", "Заказы"), ("Смены", "Календарь смен и заказов"), ("Зарплата", "Зарплата сотрудников"), ("Долги", "Долги сотрудников")):
            click_tab(page, tab)
            page.get_by_role("heading", name=heading).wait_for()
        page.get_by_role("button", name="Выйти").click()
        page.locator('input[name="username"]').wait_for()

        # Employee: personal calculation only; private tabs are absent in both menus.
        sign_in(page, "demo-employee", EMPLOYEE_PASSWORD, "Личный расчёт")
        assert page.locator('.sidebar [data-view]:visible').count() == 1
        assert page.locator('.mobile-tabs [data-view]:visible').count() == 1
        assert page.locator('.sidebar [data-view="payroll"]:visible').count() == 1
        assert page.locator('.mobile-tabs [data-view="payroll"]:visible').count() == 1
        assert page.get_by_text("Азамат").count() >= 1
        assert page.get_by_text("Айбек").count() == 0
        page.get_by_role("button", name="Выйти").click()
        page.locator('input[name="username"]').wait_for()
        print("PLAYWRIGHT OK: login/logout for 3 roles; owner/admin four tabs; employee personal-only screen")
        browser.close()


if __name__ == "__main__":
    run()
