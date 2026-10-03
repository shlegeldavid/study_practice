import sqlite3
import tkinter as tk
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk

from app_logging import LOGGER, configure_logging
from material_calculation import MaterialCalculator

from partner_database import (
    add_partner,
    connect_database,
    create_schema,
    get_all_partners,
    get_partner_by_id,
    get_partner_sales_history,
    seed_demo_data,
    seed_material_demo_data,
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
    LOGGER.error("Ошибка базы данных при попытке %s: %s", action, error)
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
            LOGGER.warning("Ошибка ввода в карточке партнера: %s", error)
            messagebox.showerror("Ошибка ввода", str(error), parent=self.window)
            return

        try:
            connection = connect_database(DATABASE_PATH)
            try:
                if self.partner_id is None:
                    add_partner(connection, partner)
                elif not update_partner(connection, self.partner_id, partner):
                    LOGGER.warning("Сохранение невозможно: партнер с ID %s отсутствует", self.partner_id)
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


class PartnerHistoryWindow:
    def __init__(
        self, parent: tk.Tk, on_close: Callable[[], None], partner_id: int
    ):
        self.partner_id = partner_id
        self.on_close = on_close
        connection = connect_database(DATABASE_PATH)
        try:
            partner = get_partner_by_id(connection, partner_id)
            if partner is None:
                raise ValueError("Партнер больше не существует. Обновите список и выберите его снова.")
            sales = get_partner_sales_history(connection, partner_id)
        finally:
            connection.close()

        self.window = tk.Toplevel(parent)
        partner_name = f'{partner["type"]} «{partner["name"]}»'
        self.window.title(f"CRM: История реализации продукции — {partner_name}")
        self.window.geometry("900x520")
        self.window.minsize(760, 420)
        self.window.configure(bg=COLORS["background"])
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.logo_image = tk.PhotoImage(file=str(RESOURCES_DIR / "company_logo.png"))
        self.icon_image = tk.PhotoImage(file=str(RESOURCES_DIR / "app_icon.png"))
        self.window.iconphoto(False, self.icon_image)

        header = tk.Frame(self.window, bg=COLORS["header"], padx=24, pady=14)
        header.pack(fill="x")
        tk.Label(header, image=self.logo_image, bg=COLORS["header"]).pack(side="left")
        titles = tk.Frame(header, bg=COLORS["header"])
        titles.pack(side="left", fill="x", expand=True, padx=(22, 0))
        tk.Label(
            titles,
            text="История реализации продукции",
            font=("Arial", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["header"],
            anchor="w",
        ).pack(fill="x")
        tk.Label(
            titles,
            text=partner_name,
            font=("Arial", 11),
            fg=COLORS["text"],
            bg=COLORS["header"],
            anchor="w",
            justify="left",
            wraplength=540,
        ).pack(fill="x", pady=(4, 0))

        main = tk.Frame(self.window, bg=COLORS["background"], padx=24, pady=20)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=1)

        style = ttk.Style(self.window)
        style.configure(
            "History.Treeview",
            font=("Arial", 10),
            rowheight=30,
            background=COLORS["card"],
            fieldbackground=COLORS["card"],
            foreground=COLORS["text"],
            bordercolor=COLORS["border"],
        )
        style.configure(
            "History.Treeview.Heading",
            font=("Arial", 10, "bold"),
            background=COLORS["header"],
            foreground=COLORS["text"],
        )
        style.map(
            "History.Treeview",
            background=[("selected", COLORS["accent"])],
            foreground=[("selected", COLORS["button_text"])],
        )
        style.map("History.Treeview.Heading", background=[("active", COLORS["header"])])

        self.table = ttk.Treeview(
            main,
            columns=("product", "quantity", "date"),
            show="headings",
            selectmode="browse",
            style="History.Treeview",
        )
        for column, title, width, minimum, anchor in (
            ("product", "Наименование продукции", 440, 260, "w"),
            ("quantity", "Количество (шт.)", 170, 150, "e"),
            ("date", "Дата продажи", 140, 130, "center"),
        ):
            self.table.heading(column, text=title, anchor="w")
            self.table.column(column, width=width, minwidth=minimum, anchor=anchor)
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(main, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(main, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        for sale in sales:
            self.table.insert(
                "", "end", values=(sale["product_name"], sale["quantity"], sale["sale_date"])
            )
        status = (
            f'Отгрузок: {len(sales)}. Всего реализовано: '
            f'{sum(int(sale["quantity"]) for sale in sales)} шт.'
            if sales else "У партнера пока нет продаж"
        )
        self.status_label = tk.Label(
            main, text=status, font=("Arial", 10),
            fg=COLORS["text"], bg=COLORS["background"], anchor="w",
        )
        self.status_label.grid(row=2, column=0, sticky="w", pady=(14, 0))
        tk.Button(
            main, text="Назад", command=self.close, font=("Arial", 10),
            bg=COLORS["accent"], fg=COLORS["button_text"],
            activebackground="#326746", activeforeground=COLORS["button_text"],
            relief="flat", padx=18, pady=7, cursor="hand2",
        ).grid(row=3, column=0, sticky="e", pady=(14, 0))
        self.window.grab_set()
        self.table.focus_set()

    def close(self) -> None:
        self.window.grab_release()
        self.window.destroy()
        self.on_close()


class MaterialCalculatorWindow:
    def __init__(self, parent: tk.Tk, on_close: Callable[[], None]):
        connection = connect_database(DATABASE_PATH)
        try:
            product_types = connection.execute(
                "SELECT id, name FROM product_types ORDER BY name"
            ).fetchall()
            material_types = connection.execute(
                "SELECT id, name FROM material_types ORDER BY name"
            ).fetchall()
        finally:
            connection.close()
        self.product_type_ids = {f"{row[0]} — {row[1]}": row[0] for row in product_types}
        self.material_type_ids = {f"{row[0]} — {row[1]}": row[0] for row in material_types}
        self.on_close = on_close
        self.window = tk.Toplevel(parent)
        self.window.title("CRM: Расчет материалов")
        self.window.geometry("620x530")
        self.window.minsize(560, 500)
        self.window.configure(bg=COLORS["background"])
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.logo_image = tk.PhotoImage(file=str(RESOURCES_DIR / "company_logo.png"))
        self.icon_image = tk.PhotoImage(file=str(RESOURCES_DIR / "app_icon.png"))
        self.window.iconphoto(False, self.icon_image)

        header = tk.Frame(self.window, bg=COLORS["header"], padx=24, pady=14)
        header.pack(fill="x")
        tk.Label(header, image=self.logo_image, bg=COLORS["header"]).pack(side="left")
        tk.Label(
            header,
            text="Расчет материалов",
            font=("Arial", 18, "bold"),
            fg=COLORS["text"],
            bg=COLORS["header"],
            padx=22,
        ).pack(side="left")

        form = tk.Frame(self.window, bg=COLORS["background"], padx=24, pady=20)
        form.pack(fill="both", expand=True)
        form.columnconfigure(1, weight=1)
        self.values = {
            name: tk.StringVar(master=self.window)
            for name in ("product_type_id", "material_type_id", "quantity", "param_1", "param_2")
        }
        self.product_type_combo = ttk.Combobox(
            form, values=tuple(self.product_type_ids), state="readonly",
            textvariable=self.values["product_type_id"], font=("Arial", 10),
        )
        self.material_type_combo = ttk.Combobox(
            form, values=tuple(self.material_type_ids), state="readonly",
            textvariable=self.values["material_type_id"], font=("Arial", 10),
        )
        self.quantity_entry = tk.Entry(
            form, textvariable=self.values["quantity"], font=("Arial", 10)
        )
        self.param_1_entry = tk.Entry(
            form, textvariable=self.values["param_1"], font=("Arial", 10)
        )
        self.param_2_entry = tk.Entry(
            form, textvariable=self.values["param_2"], font=("Arial", 10)
        )
        for row, (label, field) in enumerate((
            ("Тип продукции", self.product_type_combo),
            ("Тип материала", self.material_type_combo),
            ("Количество продукции (шт.)", self.quantity_entry),
            ("Параметр 1", self.param_1_entry),
            ("Параметр 2", self.param_2_entry),
        )):
            tk.Label(
                form, text=label, font=("Arial", 10),
                fg=COLORS["text"], bg=COLORS["background"],
            ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=7)
            field.grid(row=row, column=1, sticky="ew", pady=7)

        hint = (
            "Выберите типы из справочников. Количество — целое число больше 0.\n"
            "Оба параметра — числа больше 0, например 2,5 или 2.5."
        )
        if not product_types or not material_types:
            hint = "Справочники пусты. Заполните типы продукции и материалов в базе и откройте форму снова."
        tk.Label(
            form, text=hint, font=("Arial", 9), fg=COLORS["text"],
            bg=COLORS["background"], justify="left", wraplength=500,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(10, 16))
        self.result_var = tk.StringVar(master=self.window, value="Результат: —")
        self.result_label = tk.Label(
            form, textvariable=self.result_var, font=("Arial", 12, "bold"),
            fg=COLORS["accent"], bg=COLORS["background"],
            justify="left", wraplength=500,
        )
        self.result_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 20))
        # После изменения исходных данных старый результат уже не относится к ним.
        for variable in self.values.values():
            variable.trace_add("write", self.clear_result)

        actions = tk.Frame(form, bg=COLORS["background"])
        actions.grid(row=7, column=0, columnspan=2, sticky="e")
        self.calculate_button = tk.Button(
            actions, text="Рассчитать", command=self.calculate, font=("Arial", 10),
            bg=COLORS["accent"], fg=COLORS["button_text"],
            activebackground="#326746", activeforeground=COLORS["button_text"],
            relief="flat", padx=18, pady=7, cursor="hand2",
        )
        self.calculate_button.pack(side="left", padx=(0, 10))
        self.back_button = tk.Button(
            actions, text="Назад", command=self.close, font=("Arial", 10),
            bg=COLORS["accent"], fg=COLORS["button_text"],
            activebackground="#326746", activeforeground=COLORS["button_text"],
            relief="flat", padx=18, pady=7, cursor="hand2",
        )
        self.back_button.pack(side="left")
        self.window.grab_set()
        self.product_type_combo.focus_set()

    def clear_result(self, *args: str) -> None:
        self.result_var.set("Результат: —")

    def show_input_error(self, message: str) -> None:
        LOGGER.warning("Ошибка расчета материалов: %s", message.replace("\n", " "))
        self.result_var.set("Результат: расчет не выполнен")
        messagebox.showerror("Ошибка расчета", message, parent=self.window)

    def calculate(self) -> None:
        try:
            quantity = int(self.values["quantity"].get().strip())
            param_1 = float(self.values["param_1"].get().strip().replace(",", "."))
            param_2 = float(self.values["param_2"].get().strip().replace(",", "."))
        except ValueError:
            self.show_input_error(
                "Введите количество целым числом больше 0, а оба параметра — "
                "числами больше 0. Не оставляйте поля пустыми и удалите посторонние символы."
            )
            return

        product_type_id = self.product_type_ids.get(self.values["product_type_id"].get(), -1)
        material_type_id = self.material_type_ids.get(self.values["material_type_id"].get(), -1)
        try:
            connection = connect_database(DATABASE_PATH)
            try:
                result = MaterialCalculator(connection).calculate_material_amount(
                    product_type_id, material_type_id, quantity, param_1, param_2
                )
            finally:
                connection.close()
        except sqlite3.Error as error:
            self.result_var.set("Результат: расчет не выполнен")
            show_database_error("рассчитать количество материала", error, self.window)
            return

        if result == -1:
            self.show_input_error(
                "Не удалось рассчитать расход. Выберите существующие типы продукции "
                "и материала, введите целое количество больше 0 и положительные "
                "конечные значения обоих параметров.\n"
                "Если тип был удален, закройте калькулятор и откройте его снова. "
                "Если ввод верен, проверьте коэффициент и процент брака в справочниках."
            )
            return
        try:
            result_text = f"Необходимое количество материала: {result}"
        except ValueError:
            self.show_input_error(
                "Результат слишком велик для отображения. Уменьшите количество "
                "или параметры продукции и повторите расчет."
            )
            return
        self.result_var.set(result_text)

    def close(self) -> None:
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
        self.history_window: PartnerHistoryWindow | None = None
        self.calculator_window: MaterialCalculatorWindow | None = None
        self.selected_partner_id = tk.IntVar(master=root, value=0)
        self.partner_cards: dict[int, tk.Frame] = {}
        ttk.Style(root).theme_use("clam")

        self.prepare_database()
        self.create_header()
        self.create_main_area()
        self.refresh_partners()

    def prepare_database(self) -> None:
        connection = connect_database(DATABASE_PATH)
        try:
            create_schema(connection)
            seed_demo_data(connection)
            seed_material_demo_data(connection)
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

        actions = tk.Frame(main, bg=COLORS["background"])
        actions.pack(fill="x", pady=(0, 16))
        for text, command in (
            ("Добавить партнера", self.open_add_partner),
            ("Обновить список", self.refresh_partners),
            ("История продаж", self.open_partner_history),
        ):
            button = tk.Button(
                actions, text=text, command=command, font=("Arial", 10),
                bg=COLORS["accent"], fg=COLORS["button_text"],
                activebackground="#326746", activeforeground=COLORS["button_text"],
                relief="flat", padx=18, pady=7, cursor="hand2",
            )
            button.pack(side="left", padx=(0, 10))
            if text == "История продаж":
                self.history_button = button
                self.history_button.config(state="disabled")

        self.calculator_button = tk.Button(
            main, text="Расчет материалов", command=self.open_material_calculator,
            font=("Arial", 10), bg=COLORS["accent"], fg=COLORS["button_text"],
            activebackground="#326746", activeforeground=COLORS["button_text"],
            relief="flat", padx=18, pady=7, cursor="hand2",
        )
        self.calculator_button.pack(anchor="w", pady=(0, 12))

        list_area = tk.Frame(main, bg=COLORS["background"])
        list_area.pack(fill="both", expand=True)
        self.partner_canvas = tk.Canvas(
            list_area, bg=COLORS["background"], highlightthickness=0,
            yscrollincrement=30,
        )
        scrollbar = ttk.Scrollbar(
            list_area, orient="vertical", command=self.partner_canvas.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.partner_canvas.pack(side="left", fill="both", expand=True)
        self.partner_canvas.configure(yscrollcommand=scrollbar.set)
        self.partner_list = tk.Frame(self.partner_canvas, bg=COLORS["background"])
        list_item = self.partner_canvas.create_window(
            (0, 0), window=self.partner_list, anchor="nw"
        )
        self.partner_list.bind(
            "<Configure>",
            lambda event: self.partner_canvas.configure(scrollregion=self.partner_canvas.bbox("all")),
        )
        self.partner_canvas.bind(
            "<Configure>", lambda event: self.partner_canvas.itemconfigure(list_item, width=event.width)
        )
        self.root.bind("<MouseWheel>", self.scroll_partners)

        self.status_label = tk.Label(
            main,
            text="",
            font=("Arial", 9),
            fg="#555555",
            bg=COLORS["background"],
        )
        self.status_label.pack(anchor="w", pady=(4, 0))

    def scroll_partners(self, event: tk.Event) -> None:
        if self.partner_canvas.yview() != (0.0, 1.0):
            self.partner_canvas.yview_scroll(-int(event.delta / 120), "units")

    def select_partner(self, partner_id: int) -> None:
        self.selected_partner_id.set(partner_id)
        self.update_partner_selection()

    def update_partner_selection(self) -> None:
        selected = self.selected_partner_id.get()
        for partner_id, card in self.partner_cards.items():
            card.config(
                highlightbackground=COLORS["accent"] if partner_id == selected else COLORS["border"]
            )
        self.history_button.config(state="normal" if selected in self.partner_cards else "disabled")

    def open_partner_history(self) -> None:
        if self.history_window is not None:
            self.history_window.window.lift()
            return
        partner_id = self.selected_partner_id.get()
        if partner_id not in self.partner_cards:
            messagebox.showwarning(
                "Партнер не выбран", "Выберите партнера в списке.", parent=self.root
            )
            return
        try:
            self.history_window = PartnerHistoryWindow(
                self.root, self.on_history_close, partner_id
            )
        except sqlite3.Error as error:
            show_database_error("загрузить историю продаж", error, self.root)
        except ValueError as error:
            LOGGER.warning("Не удалось открыть историю продаж: %s", error)
            messagebox.showerror("Партнер не найден", str(error), parent=self.root)

    def on_history_close(self) -> None:
        self.history_window = None
        self.root.focus_set()

    def open_material_calculator(self) -> None:
        if self.calculator_window is not None:
            self.calculator_window.window.lift()
            return
        try:
            self.calculator_window = MaterialCalculatorWindow(self.root, self.on_calculator_close)
        except sqlite3.Error as error:
            show_database_error("загрузить справочники материалов", error, self.root)

    def on_calculator_close(self) -> None:
        self.calculator_window = None
        self.root.focus_set()

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
            LOGGER.warning("Редактирование невозможно: партнер с ID %s отсутствует", partner_id)
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
        self.partner_cards.clear()
        if self.selected_partner_id.get() not in {p["partner_id"] for p in partners}:
            self.selected_partner_id.set(0)

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
        self.update_partner_selection()

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
        partner_id = int(partner["partner_id"])
        self.partner_cards[partner_id] = card

        tk.Radiobutton(
            card,
            text=f'{partner["type"]} | {partner["name"]}',
            variable=self.selected_partner_id,
            value=partner_id,
            command=self.update_partner_selection,
            activebackground=COLORS["card"],
            activeforeground=COLORS["text"],
            selectcolor=COLORS["card"],
            cursor="hand2",
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
        for widget in (card, *card.winfo_children()):
            if isinstance(widget, (tk.Frame, tk.Label)):
                widget.bind("<Button-1>", lambda event, pid=partner_id: self.select_partner(pid))


def main() -> None:
    configure_logging()
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
