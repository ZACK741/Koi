from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
import selenium.common.exceptions as Selenium_EX
import json


class DataCollector(object):
    def __init__(self):
        self.action = None
        self.dynamicProps = None
        self.lastFind = None
        self.book = {}
        self.structs = []
        self.commands = {
            "direct":
                lambda: self.direct_web(),
            "find":
                lambda : self.find_element(),
            "dump":
                lambda: self.dump_element(),
            "construct":
                lambda: self.make_book(),
            "input":
                lambda: self.key_in(),
            "bye":
                lambda: self.bye(),
            "locate":
                lambda: self.locate(),
            "extend":
                lambda: self.extending(),
            "pass":
                lambda: self.pass_it(),
            "download":
                lambda: self.downloading(),
            "remove":
                lambda: self.remove_element(),
            "chain":
                lambda: self.chain_actions(),
            "clear":
                lambda: self.clearing()
        }

        with open('./config/onboarding.json', 'r') as f:
            self.moving_path = json.load(f)

        self.options = webdriver.ChromeOptions()
        settings = {
               "recentDestinations": [{
                    "id": "Save as PDF",
                    "origin": "local",
                    "account": "",
                }],
                "selectedDestinationId": "Save as PDF",
                "version": 2
            }
        prefs = {'printing.print_preview_sticky_settings.appState': json.dumps(settings)}
        self.options.add_experimental_option('prefs', prefs)
        self.options.add_argument('--kiosk-printing')
        self.browser = None

    def direct_web(self):
        link = self.dynamicProps
        self.browser.get(link)

    def clearing(self):
        self.lastFind = None

    def remove_element(self):
        type, name = self.dynamicProps.split('->')
        element = self.browser.find_element(getattr(By, type), name)
        self.browser.execute_script("""
        var element = arguments[0];
        element.parentNode.removeChild(element);
        """, element)

    def pass_it(self):
        pass

    def chain_actions(self):
        actionList = self.dynamicProps.split(',')
        action = ActionChains(self.browser)
        for act in actionList:
            if act == "":
                continue
            if act == "@":
                getattr(action, 'click')(self.lastFind)
                continue
            func, ele = act.split('=>')
            types, name = ele.split('->')
            self.run(f'find|:|{types}->{name}')
            getattr(action, func)(self.lastFind)
        action.perform()

    def find_element(self):
        type, name = self.dynamicProps.split('->')
        while True:
            try:
                self.lastFind = self.browser.find_element(getattr(By, type), name)
                break
            except Selenium_EX.NoSuchElementException:
                continue

    def downloading(self):
        self.browser.execute_script('window.print();')

    def extending(self):
        type, name = self.dynamicProps.split('->')
        while True:
            try:
                self.lastFind = self.lastFind.find_element(getattr(By, type), name)
                break
            except Selenium_EX.NoSuchElementException:
                continue

    def locate(self):
        indx, props = self.dynamicProps.split(',')
        type, names = props.split('->')
        while True:
            try:
                self.lastFind = self.lastFind.find_elements(getattr(By, type), names)[int(indx)]
                break
            except Selenium_EX.InvalidSelectorException:
                continue
            except Selenium_EX.StaleElementReferenceException:
                continue
            except IndexError:
                print([_.text for _ in self.lastFind.find_elements(getattr(By, type), names)])

    def rooting(self, element):
        content = element.find_elements_by_xpath("./*")
        for c in content:
            if c.get_property("tagName").lower() == "table":
                table = []
                # row
                row = c.find_element(By.TAG_NAME,"tbody").find_elements_by_xpath("./*")
                # col
                for r in row:
                    col = [_.text.replace("\n", "") for _ in r.find_elements(By.TAG_NAME,"td") if _.text not in ["","\n"]]
                    if col != []:
                        table.append(col)
                return table

        if len(content) != 0:
            l = [_.text.replace("\n", "") for _ in content if not isinstance(_, list) and _.text not in ["","\n"]]
            return l

        return ["null"]

    def dump_element(self):
        self.structs = []
        findList = self.lastFind.find_elements_by_xpath("./*")
        dumped = {}
        tags = ["id", "className", "tagName"]
        ignore = self.dynamicProps.split(',')

        for c in findList:
            for t in tags:
                p = c.get_property(t)
                if p and p not in ignore:
                    try:
                        dumped[c.get_property(t)] += self.rooting(c)
                    except KeyError:
                        dumped[c.get_property(t)] = self.rooting(c)
                    break
        links = self.lastFind.find_elements(By.TAG_NAME, "a")
        if links and "links" not in ignore:
            dumped["links"] = [{"link":_.get_property('href'),"header":_.text.replace("\n", " ")} for _ in links]
        self.structs.append(dumped)
        print(json.dumps(self.structs, indent=4))

    def key_in(self):
        keys = self.dynamicProps.split(",")
        for key in keys:
            if key == "@":
                self.lastFind.click()
            else:
                self.lastFind.send_keys(key)

    def make_book(self):
        nameList = self.dynamicProps.split(",")
        size = len(self.book.keys())
        for s in self.structs:
            for name in nameList:
                if name == " ":
                    continue
                try:
                    new, old = name.split(':')
                    try:
                        s[new] = s.pop(old)
                    except KeyError:
                        pass
                except ValueError:
                    print("value error on name: ",name)

            self.book[f'page_{size}'] = s
            size += 1

    def bye(self):
        self.browser.close()
        self.browser.quit()

    def break_down_command(self, commandString):
        commandString = commandString.replace('\n', '')
        commandString = commandString.split('|;|')
        commandList = []
        for _ in commandString:
            if _ == "":
                continue
            label, prop = _.split('|:|')
            commandList.append([label, prop])
        return commandList

    def run(self, commands):
        if not self.browser:
            chromedriver = './chromedriver.exe'
            self.browser = webdriver.Chrome(chromedriver, chrome_options=self.options)
            self.action = ActionChains(self.browser)
            self.browser.set_window_size(1440, 900)
        commands = self.break_down_command(commands)
        for command in commands:
            print(command)
            label, self.dynamicProps = command
            self.commands[label]()

    def run_line(self, commands):
        if not self.browser:
            chromedriver = './chromedriver.exe'
            self.browser = webdriver.Chrome(chromedriver, chrome_options=self.options)
            self.action = ActionChains(self.browser)
            self.browser.set_window_size(1440, 900)
        commands = commands.replace('\n', '')
        commands = commands.replace('|;|', "")
        label, self.dynamicProps = commands.split('|:|')
        self.commands[label]()


# direct    |:| <link>                  |;|
# extend    |:| <key->name>             |;|
# find      |:| <key->name>             |;|
# dump      |:| <[undesired items]>     |;|
# construct |:| <null>                  |;|
# input     |:| <keys, @>               |;|
# bye       |:| <null>                  |;|
# locate    |:| <index> |&| <key->name> |;|
