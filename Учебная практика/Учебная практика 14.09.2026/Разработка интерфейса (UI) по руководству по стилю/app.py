import tkinter as tk
from pathlib import Path
from tkinter import messagebox


BASE_DIR = Path(__file__).resolve().parent
RESOURCES_DIR = BASE_DIR / "resources"

COLORS = {
    "background": "#f3f3f3",
    "card": "#ffffff",
    "header": "#e8f1e9",
    "border": "#8a8a8a",
    "text": "#202020",
    "accent": "#3f7f56",
    "button_text": "#ffffff",
}


PARTNERS = [
    {
        "type": "ООО",
        "name": "Ромашка",
        "director": "Иванов Иван Иванович",
        "phone": "+7 223 322 22 32",
        "rating": 10,
        "discount": 5,
    },
    {
        "type": "ООО",
        "name": "Вектор",
        "director": "Петров Пётр Петрович",
        "phone": "+7 495 120 45 67",
        "rating": 8,
        "discount": 10,
    },
    {
        "type": "ИП",
        "name": "Север",
        "director": "Сидорова Анна Олеговна",
        "phone": "+7 812 765 43 21",
        "rating": 9,
        "discount": 15,
    },
]


class PartnerApplication:
    def __init__(self, root):
        self.root = root
        self.root.title("CRM: Список партнеров и скидок")
        self.root.geometry("760x590")
        self.root.minsize(650, 520)
        self.root.configure(bg=COLORS["background"])

        self.logo_image = tk.PhotoImage(
            file=str(RESOURCES_DIR / "company_logo.png")
        )
        self.icon_image = tk.PhotoImage(file=str(RESOURCES_DIR / "app_icon.png"))
        self.root.iconphoto(True, self.icon_image)

        self.create_header()
        self.create_main_area()

    def create_header(self):
        header = tk.Frame(self.root, bg=COLORS["header"], padx=24, pady=14)
        header.pack(fill="x")

        logo = tk.Label(header, image=self.logo_image, bg=COLORS["header"])
        logo.pack(side="left")

        title = tk.Label(
            header,
            text="Список партнеров и скидок",
            font=("Arial", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["header"],
            padx=22,
        )
        title.pack(side="left")

    def create_main_area(self):
        main = tk.Frame(self.root, bg=COLORS["background"], padx=24, pady=20)
        main.pack(fill="both", expand=True)

        for partner in PARTNERS:
            self.create_partner_card(main, partner)

        button = tk.Button(
            main,
            text="Обновить список",
            command=self.show_refresh_message,
            font=("Arial", 10),
            bg=COLORS["accent"],
            fg=COLORS["button_text"],
            activebackground="#326746",
            activeforeground=COLORS["button_text"],
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
        )
        button.pack(anchor="e", pady=(2, 0))

    def create_partner_card(self, parent, partner):
        card = tk.Frame(
            parent,
            bg=COLORS["card"],
            highlightbackground=COLORS["border"],
            highlightthickness=1,
            padx=24,
            pady=13,
        )
        card.pack(fill="x", pady=(0, 14))
        card.columnconfigure(0, weight=1)

        name_text = f'{partner["type"]} | {partner["name"]}'
        name = tk.Label(
            card,
            text=name_text,
            font=("Arial", 13),
            fg=COLORS["text"],
            bg=COLORS["card"],
            anchor="w",
        )
        name.grid(row=0, column=0, sticky="w")

        discount = tk.Label(
            card,
            text=f'{partner["discount"]}%',
            font=("Arial", 13),
            fg=COLORS["text"],
            bg=COLORS["card"],
            anchor="e",
        )
        discount.grid(row=0, column=1, sticky="e", padx=(20, 30))

        details = (
            f'{partner["director"]}\n'
            f'{partner["phone"]}\n'
            f'Рейтинг: {partner["rating"]}'
        )
        info = tk.Label(
            card,
            text=details,
            font=("Arial", 10),
            fg=COLORS["text"],
            bg=COLORS["card"],
            justify="left",
            anchor="w",
        )
        info.grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 0))

    def show_refresh_message(self):
        messagebox.showinfo("Обновление", "Список партнеров обновлён")


def main():
    root = tk.Tk()
    PartnerApplication(root)
    root.mainloop()


if __name__ == "__main__":
    main()
