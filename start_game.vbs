Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\Users\Utilisateur\Desktop\Pokemon"
WshShell.Run "python run_game.py", 1, False
