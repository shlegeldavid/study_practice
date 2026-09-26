import sqlite3
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from partner_database import (
    add_partner,
    connect_database,
    create_schema,
    get_all_partners,
    get_partner_by_id,
    seed_demo_data,
    update_partner,
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


def validate_partner_fields(
    values: dict[str, str], allowed_types: tuple[str, ...]
) -> dict[str, object]:
    name = values["name"].strip()
    email = values["email"].strip()
    if not name:
        raise ValueError("Введите наименование партнера и повторите сохранение.")
    if not email:
        raise ValueError("Введите email компании и повторите сохранение.")
    if values["type"] not in allowed_types:
        raise ValueError("Выберите тип партнера из списка и повторите сохранение.")

    try:
        rating = int(values["rating"].strip())
    except ValueError:
        raise ValueError(
            "Рейтинг должен быть целым числом от 0. Удалите дробную часть "
            "или посторонние символы и повторите попытку."
        ) from None
    if rating < 0:
        raise ValueError(
            "Рейтинг должен быть целым числом от 0. Удалите знак минуса "
            "и повторите попытку."
        )
    if rating > 2**63 - 1:
        raise ValueError("Рейтинг слишком большой. Уменьшите число и повторите попытку.")

    return {
        "name": name,
        "type": values["type"],
        "rating": rating,
        "address": values["address"].strip(),
        "director": values["director"].strip(),
        "phone": values["phone"].strip(),
        "email": email,
    }


def show_database_error(action: str, error: sqlite3.Error, parent: tk.Misc) -> None:
    messagebox.showerror(
        "Ошибка базы данных",
        f"Не удалось {action}.\n"
        "Проверьте доступ к файлу partners.db и закройте программы, которые "
        "могут его использовать. Если файл поврежден, восстановите его из "
        "копии. Затем повторите попытку.\n"
        f"Подробности: {error}",
        parent=parent,
    )


class PlaceholderEntry(tk.Entry):
    def __init__(self, parent: tk.Misc, placeholder: str):
        super().__init__(parent, font=("Arial", 10), fg=COLORS["text"])
        self.placeholder = placeholder
        self.placeholder_visible = False
        self.bind("<FocusIn>", self.hide_placeholder)
        self.bind("<FocusOut>", self.show_placeholder)
        self.show_placeholder()

    def show_placeholder(self, event: tk.Event | None = None) -> None:
        if not super().get():
            self.placeholder_visible = True
            self.config(fg="#777777")
            self.insert(0, self.placeholder)

    def hide_placeholder(self, event: tk.Event | None = None) -> None:
        if self.placeholder_visible:
            self.delete(0, tk.END)
            self.config(fg=COLORS["text"])
            self.placeholder_visible = False

    def get(self) -> str:
        # Текст подсказки не должен считаться введенным значением.
        return "" if self.placeholder_visible else super().get()

    def set_value(self, value: str) -> None:
        self.hide_placeholder()
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
        else:
            self.show_placeholder()


class PartnerEditWindow:
    def __init__(
        self,
        parent: tk.Tk,
        on_close: Callable[[], None],
        on_saved: Callable[[], None],
        partner: dict[str, object] | None = None,
    ):
        self.parent = parent
        self.partner_id = int(partner["partner_id"]) if partner is not None else None
        self.on_close = on_close
        self.on_saved = on_saved
        mode = "Редактирование" if partner is not None else "Добавление"
        self.window = tk.Toplevel(parent)
        self.window.title(f"CRM: Карточка партнера [{mode}]")
        self.window.geometry("540x530")
        self.window.minsize(480, 490)
        self.window.configure(bg=COLORS["background"])
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        form = tk.Frame(self.window, bg=COLORS["background"], padx=24, pady=20)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)

        tk.Label(
            form,
            text=f"{mode} партнера",
            font=("Arial", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["background"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 18))

        self.name_entry = tk.Entry(form, font=("Arial", 10))
        # readonly запрещает ввод типа, которого нет в списке.
        self.type_combo = ttk.Combobox(
            form,
            values=("ЗАО", "ООО", "ИП", "АО", "ПАО"),
            state="readonly",
            font=("Arial", 10),
        )
        self.rating_entry = tk.Entry(form, font=("Arial", 10))
        self.address_entry = tk.Entry(form, font=("Arial", 10))
        self.director_entry = tk.Entry(form, font=("Arial", 10))
        self.phone_entry = PlaceholderEntry(form, "+7 (999) 123-45-67")
        self.email_entry = PlaceholderEntry(form, "info@company.ru")

        fields = (
            ("Наименование", self.name_entry),
            ("Тип партнера", self.type_combo),
            ("Рейтинг", self.rating_entry),
            ("Адрес", self.address_entry),
            ("ФИО директора", self.director_entry),
            ("Телефон", self.phone_entry),
            ("Email компании", self.email_entry),
        )
        for row, (label, field) in enumerate(fields, start=1):
            tk.Label(
                form,
                text=label,
                font=("Arial", 10),
                fg=COLORS["text"],
                bg=COLORS["background"],
            ).grid(row=row, column=0, sticky="w", pady=7, padx=(0, 12))
            field.grid(row=row, column=1, sticky="ew", pady=7)

        if partner is not None:
            self.name_entry.insert(0, str(partner["name"]))
            self.type_combo.set(str(partner["type"]))
            self.rating_entry.insert(0, str(partner["rating"]))
            self.address_entry.insert(0, str(partner["address"]))
            self.director_entry.insert(0, str(partner["director"]))
            self.phone_entry.set_value(str(partner["phone"]))
            self.email_entry.set_value(str(partner["email"]))

        self.initial_values = self.form_values()

        actions = tk.Frame(form, bg=COLORS["background"])
        actions.grid(row=8, column=1, sticky="e", pady=(22, 0))
        tk.Button(
            actions,
            text="Назад",
            command=self.close,
            font=("Arial", 10),
            bg=COLORS["accent"],
            fg=COLORS["button_text"],
            activebackground="#326746",
            activeforeground=COLORS["button_text"],
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            actions,
            text="Сохранить",
            command=self.save,
            font=("Arial", 10),
            bg=COLORS["accent"],
            fg=COLORS["button_text"],
            activebackground="#326746",
            activeforeground=COLORS["button_text"],
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
        ).pack(side="left")

        self.window.grab_set()
        self.window.focus_set()

    def form_values(self) -> dict[str, str]:
        return {
            "name": self.name_entry.get(),
            "type": self.type_combo.get(),
            "rating": self.rating_entry.get(),
            "address": self.address_entry.get(),
            "director": self.director_entry.get(),
            "phone": self.phone_entry.get(),
            "email": self.email_entry.get(),
        }

    def save(self) -> None:
        try:
            partner = validate_partner_fields(
                self.form_values(), tuple(self.type_combo.cget("values"))
            )
        except ValueError as error:
            messagebox.showerror("Ошибка ввода", str(error), parent=self.window)
            return

        try:
            connection = connect_database(DATABASE_PATH)
            try:
                if self.partner_id is None:
                    add_partner(connection, partner)
                elif not update_partner(connection, self.partner_id, partner):
                    messagebox.showerror(
                        "Партнер не найден",
                        "Запись больше не существует. Обновите список и выберите партнера снова.",
                        parent=self.window,
                    )
                    return
            finally:
                connection.close()
        except sqlite3.Error as error:
            show_database_error("сохранить партнера", error, self.window)
            return

        self.finish_close()
        self.on_saved()
        title = "Партнер добавлен" if self.partner_id is None else "Изменения сохранены"
        messagebox.showinfo(
            title,
            "Данные партнера успешно сохранены в базе данных.",
            parent=self.parent,
        )

    def close(self) -> None:
        if self.form_values() != self.initial_values:
            confirmed = messagebox.askyesno(
                "Несохраненные изменения",
                "Изменения не сохранены. Если закрыть карточку, они будут "
                "безвозвратно потеряны. Закрыть без сохранения?",
                icon=messagebox.WARNING,
                parent=self.window,
            )
            if not confirmed:
                return
        self.finish_close()

    def finish_close(self) -> None:
        self.window.grab_release()
        self.window.destroy()
        self.on_close()


class MainWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("CRM: Реестр партнеров")
        self.root.geometry("760x640")
        self.root.minsize(650, 520)
        self.root.configure(bg=COLORS["background"])

        self.logo_image = tk.PhotoImage(file=str(RESOURCES_DIR / "company_logo.png"))
        self.icon_image = tk.PhotoImage(file=str(RESOURCES_DIR / "app_icon.png"))
        self.root.iconphoto(True, self.icon_image)
        self.edit_window: PartnerEditWindow | None = None

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
            text="Реестр партнеров",
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

        for text, command in (
            ("Обновить список", self.refresh_partners),
            ("Добавить партнера", self.open_add_partner),
        ):
            tk.Button(
                main,
                text=text,
                command=command,
                font=("Arial", 10),
                bg=COLORS["accent"],
                fg=COLORS["button_text"],
                activebackground="#326746",
                activeforeground=COLORS["button_text"],
                relief="flat",
                padx=18,
                pady=7,
                cursor="hand2",
            ).pack(side="right", padx=(10, 0), pady=(4, 0))

    def open_add_partner(self) -> None:
        if self.edit_window is not None:
            self.edit_window.window.lift()
            return
        self.edit_window = PartnerEditWindow(
            self.root, self.on_edit_close, self.refresh_partners
        )

    def open_edit_partner(self, partner_id: int) -> None:
        if self.edit_window is not None:
            self.edit_window.window.lift()
            return
        try:
            connection = connect_database(DATABASE_PATH)
            try:
                partner = get_partner_by_id(connection, partner_id)
            finally:
                connection.close()
        except sqlite3.Error as error:
            show_database_error("открыть партнера", error, self.root)
            return
        if partner is None:
            messagebox.showerror(
                "Партнер не найден",
                "Запись больше не существует. Обновите список и выберите партнера снова.",
                parent=self.root,
            )
            return
        self.edit_window = PartnerEditWindow(
            self.root, self.on_edit_close, self.refresh_partners, partner
        )

    def on_edit_close(self) -> None:
        self.edit_window = None
        self.root.focus_set()

    def refresh_partners(self) -> None:
        try:
            connection = connect_database(DATABASE_PATH)
            try:
                partners = get_all_partners(connection)
            finally:
                connection.close()
        except sqlite3.Error as error:
            show_database_error("загрузить список партнеров", error, self.root)
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
        ).grid(row=1, column=0, sticky="w", pady=(3, 0))

        # Аргумент по умолчанию сохраняет ID именно этой карточки.
        tk.Button(
            card,
            text="Редактировать",
            command=lambda partner_id=partner["partner_id"]: self.open_edit_partner(int(partner_id)),
            font=("Arial", 9),
            bg=COLORS["accent"],
            fg=COLORS["button_text"],
            activebackground="#326746",
            activeforeground=COLORS["button_text"],
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        ).grid(row=1, column=1, sticky="e", pady=(3, 0))


def main() -> None:
    root = tk.Tk()
    try:
        MainWindow(root)
    except sqlite3.Error as error:
        show_database_error("открыть базу данных", error, root)
        root.destroy()
        return
    root.mainloop()


if __name__ == "__main__":
    main()
