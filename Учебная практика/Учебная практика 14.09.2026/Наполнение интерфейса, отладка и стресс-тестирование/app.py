import sqlite3
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from partner_database import (
    connect_database,
    create_schema,
    get_all_partners,
    seed_demo_data,
)


BASE_DIR = Path(__file__).resolve().parent
RESOURCES_DIR = BASE_DIR / "resources"
DATABASE_PATH = BASE_DIR / "partners.db"

COLORS = {
    "background": "#f3f3f3",
    "card": "#ffffff",
    "header": "#e8f1e9",
    "border": "#8a8a8a",
    "text": "#202020",
    "accent": "#3f7f56",
    "button_text": "#ffffff",
}


class PartnerApplication:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CRM: Список партнеров и скидок")
        self.root.geometry("760x640")
        self.root.minsize(650, 520)
        self.root.configure(bg=COLORS["background"])

        self.logo_image = tk.PhotoImage(file=str(RESOURCES_DIR / "company_logo.png"))
        self.icon_image = tk.PhotoImage(file=str(RESOURCES_DIR / "app_icon.png"))
        self.root.iconphoto(True, self.icon_image)

        self.prepare_database()
        self.create_header()
        self.create_main_area()
        self.refresh_partners()

    def prepare_database(self) -> None:
        connection = connect_database(DATABASE_PATH)
        try:
            create_schema(connection)
            seed_demo_data(connection)
        finally:
            connection.close()

    def create_header(self) -> None:
        header = tk.Frame(self.root, bg=COLORS["header"], padx=24, pady=14)
        header.pack(fill="x")

        tk.Label(header, image=self.logo_image, bg=COLORS["header"]).pack(side="left")
        tk.Label(
            header,
            text="Список партнеров и скидок",
            font=("Arial", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["header"],
            padx=22,
        ).pack(side="left")

    def create_main_area(self) -> None:
        main = tk.Frame(self.root, bg=COLORS["background"], padx=24, pady=20)
        main.pack(fill="both", expand=True)

        self.partner_list = tk.Frame(main, bg=COLORS["background"])
        self.partner_list.pack(fill="both", expand=True)

        self.status_label = tk.Label(
            main,
            text="",
            font=("Arial", 9),
            fg="#555555",
            bg=COLORS["background"],
        )
        self.status_label.pack(side="left", pady=(4, 0))

        tk.Button(
            main,
            text="Обновить список",
            command=self.refresh_partners,
            font=("Arial", 10),
            bg=COLORS["accent"],
            fg=COLORS["button_text"],
            activebackground="#326746",
            activeforeground=COLORS["button_text"],
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
        ).pack(side="right", pady=(4, 0))

    def refresh_partners(self) -> None:
        try:
            connection = connect_database(DATABASE_PATH)
            try:
                partners = get_all_partners(connection)
            finally:
                connection.close()
        except sqlite3.Error as error:
            messagebox.showerror("Ошибка базы данных", f"Не удалось загрузить партнеров:\n{error}")
            return

        for widget in self.partner_list.winfo_children():
            widget.destroy()

        if not partners:
            tk.Label(
                self.partner_list,
                text="В базе данных пока нет партнеров",
                font=("Arial", 11),
                fg=COLORS["text"],
                bg=COLORS["background"],
            ).pack(pady=30)
        else:
            for partner in partners:
                self.create_partner_card(partner)

        self.status_label.config(text=f"Загружено партнеров: {len(partners)}")

    def create_partner_card(self, partner: dict[str, object]) -> None:
        card = tk.Frame(
            self.partner_list,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=24,
            pady=11,
        )
        card.pack(fill="x", pady=(0, 12))
        card.columnconfigure(0, weight=1)

        tk.Label(
            card,
            text=f'{partner["type"]} | {partner["name"]}',
            font=("Arial", 13),
            fg=COLORS["text"],
            bg=COLORS["card"],
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            card,
            text=f'{partner["discount_percent"]}%',
            font=("Arial", 13, "bold"),
            fg=COLORS["text"],
            bg=COLORS["card"],
            anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(20, 30))

        details = (
            f'{partner["director"]}\n'
            f'{partner["phone"]}\n'
            f'Рейтинг: {partner["rating"]}'
        )
        tk.Label(
            card,
            text=details,
            font=("Arial", 10),
            fg=COLORS["text"],
            bg=COLORS["card"],
            justify="left",
            anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))


def main() -> None:
    root = tk.Tk()
    PartnerApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
