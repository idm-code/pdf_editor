import tkinter as tk
from app.ui.main_window import MainWindow

def main():
    root = tk.Tk()
    root.title('PDF Editor - M1')
    root.geometry('1024x768')
    MainWindow(root)
    root.mainloop()

if __name__ == '__main__':
    main()
