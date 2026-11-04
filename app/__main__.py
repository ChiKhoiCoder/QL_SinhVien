from app.database.schema import initialize_database
from app.ui.main_window import MainWindow


def main() -> None:
    initialize_database()
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
