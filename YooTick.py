version='1.1'
import os, json, datetime, requests, difflib

import disnake
from disnake.ext import commands
import asyncio  

intents = disnake.Intents.default() 
intents.message_content = True

class ButtonView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

class PersistentViewBot(commands.Bot):
    def __init__(self, activity=None):
        super().__init__(command_prefix='$', intents=intents, activity=activity)
        self.persistent_views_added = False
        self.sent_message = False
        self.config_file = 'config.json'
        with open(self.config_file, 'r') as f:
            self.config = json.load(f)
        self.sent_message = self.config.get('sent_message', False)
        self.ticket_counter = self.config.get('ticket_counter', 0)
        self.staff_members = self.config.get('staff_members', {})
        self.dev_members = self.config.get('dev_members', [])
        self.TICKET_CHANNEL_ID = self.config.get('TICKET_CHANNEL_ID')
        self.REQUEST_CHANNEL_ID = self.config.get('REQUEST_CHANNEL_ID')
        self.CATEGORY_ID = self.config.get('CATEGORY_ID')
        self.qa_pairs = self.load_qa_pairs()
        self.qa_enabled = self.config.get('qa_enabled', True)

        self.config.setdefault('date_stats', {})

    def config_clear(self, user=None):
        staff_members = self.config.get('staff_members', {})
        if user:
            if user.lower() in staff_members:
                staff_members[user.lower()]['claimed_tickets'] = []
                staff_members[user.lower()]['claimed_ticket_users'] = {}
                self.config['staff_members'] = staff_members
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                return f"Мусор в конфиге для {user} был очищен."
            else:
                return f"Пользователь - {user} не был найден в списке staff."
        else:
            for staff_member in staff_members:
                staff_members[staff_member]['claimed_tickets'] = []
                staff_members[staff_member]['claimed_ticket_users'] = {}
            self.config['staff_members'] = staff_members
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return "Мусор в конфиге для всех сотрудников был очищен."

    def config_view(self):
        staff_members = self.config.get('staff_members', {})
        result = ""
        for staff_member, info in staff_members.items():
            result += f"**{staff_member}**:\n"
            result += f"Claimed Tickets: {info.get('claimed_tickets', [])}\n"
            result += f"Claimed Ticket Users: {info.get('claimed_ticket_users', {})}\n\n"
        return result

    def load_qa_pairs(self):
        qa_pairs = {}
        response = requests.get('https://raw.githubusercontent.com/Anarchowitz/YooTick/main/qa_pairs.txt')
        if response.status_code == 200:
            for line in response.text.splitlines():
                line = line.strip()
                if line:
                    if ' ' in line:
                        parts = line.split('|')
                        if len(parts) == 2:
                            question, answer = parts
                            qa_pairs[question] = answer
                        else:
                            print(f"Invalid line format: {line}")
                    else:
                        print(f"Skipping line without ' ': {line}")
        else:
            print(f"Error loading QA pairs: {response.status_code}")
        return qa_pairs

    async def on_ready(self):
        if not self.persistent_views_added:
            self.persistent_views_added = True

        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            self.config.update(config)

        channel = self.get_channel(self.TICKET_CHANNEL_ID)
        if channel:
            if not self.config.get('sent_message', False):
                await asyncio.sleep(5)
                embed = disnake.Embed(
                    title="Связь с администрацией",
                    description="При подаче запроса укажите все необходимые данные для **оперативного** решения вопроса. Соблюдайте **правила** общения, чтобы избежать **блокировки доступа** к созданию запросов.",
                    timestamp=datetime.datetime.now(),
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                view = disnake.ui.View()
                button = disnake.ui.Button(label='Задать вопрос', style=disnake.ButtonStyle.green, emoji='📨', custom_id='create_ticket')
                view.add_item(button)
                message = await channel.send(embed=embed, view=view)

                self.config['sent_message'] = True
                with open(self.config_file, 'r+') as f:
                    config_data = json.load(f)
                    config_data['sent_message'] = True
                    f.seek(0)
                    json.dump(config_data, f)
                    f.truncate()

        print(f"Logged in as {self.user} (ID: {self.user.id})\n------")

    async def on_message(self, message):
        if message.author == self.user:
            return
        
        if message.content.startswith('$help'):
            await message.delete()
            if message.author.name.lower() in self.config.get('staff_members', {}):
                embed = disnake.Embed(
                    title="Рабочие команды бота",
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                embed.add_field(
                    name="$claim",
                    value="`Взять тикет на себя\n Права доступа -> staff_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$close",
                    value="`Закрыть тикет\n Права доступа -> staff_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$info",
                    value="`Информация про бота.\n Права доступа -> staff_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$list_rights",
                    value="`Информация про всех участников с правами.\n Права доступа -> staff_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$list_helper",
                    value="`Информация про быстрые сокращение (формы) по словам.\n Права доступа -> staff_members.`",
                    inline=False
                )
                embed.add_field(
                    name="------",
                    value=" ",
                    inline=False
                )
                embed.add_field(
                    name="$add_rights",
                    value="`Добавить права пользователю\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$del_rights",
                    value="`Убрать права у пользователя\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$add_staff_role",
                    value="`Добавить роль в список staff_roles\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$del_staff_role",
                    value="`Убрать роль из списка staff_roles\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$qa_on",
                    value="`Включить авто-ответчик\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$qa_off",
                    value="`Выключить авто-ответчик\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$stats",
                    value="`Показать топ по закрытым тикетам\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$secret_stats",
                    value="`Показать статистику количество закрытых тикетов.\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$date_stats",
                    value="`Показать статистику закрытых тикетов за дату\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$set",
                    value="`Установить количество закрытых тикетов для staff_member\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$sum",
                    value="`Прибавить/убавить количество закрытых тикетов для staff_member\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$date_set_stats",
                    value="`Установить количество закрытых тикетов за дату\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$config_view",
                    value="`Посмотреть наличие лишнего мусора в конфиге\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$config_clear",
                    value="`Очистка конфига от лишнего мусора\n(Рекомендуется: когда тикетов нету)\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$config_date_clear",
                    value="`Очистить даты в date_stats конфиге.\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$config_date_clear",
                    value="`Очистить даты в date_stats конфиге.\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$clear_tickets",
                    value="`Очистить список созданных тикетов людьми (created_tickets.json).\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$tickets_num",
                    value="`Установить количество созданных тикетов\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.add_field(
                    name="$primetime",
                    value="`Установить рабочее время\n Права доступа -> dev_members.`",
                    inline=False
                )
                embed.set_footer(
                    text="maded by anarchowitz ",
                    icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для staff_members!")

        if message.content.startswith('$claim'):
            await message.delete()
            if "ticket" in message.channel.name.lower() and message.author.name.lower() in self.config.get('staff_members', {}):
                await self.claim_ticket(message)
            elif "ticket" not in message.channel.name.lower():
                await message.channel.send("Эта команда доступна только в каналах с названием содержащим слово 'ticket'!")
            else:
                await message.channel.send("Эта команда доступна только для staff_members!")

        elif message.content.startswith('$close'):
            await message.delete()
            if "ticket" in message.channel.name.lower() and message.author.name.lower() in self.config.get('staff_members', {}):
                await self.close_ticket(message)
            elif "ticket" not in message.channel.name.lower():
                await message.channel.send("Эта команда доступна только в каналах с названием содержащим слово 'ticket'!")
            else:
                await message.channel.send("Эта команда доступна только для staff_members!")
    
        if message.content.startswith('$add_rights'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) == 3:
                    username = args[1]
                    role = args[2]
                    if role.lower() == 'staff':
                        self.config['staff_members'][username] = {'claimed_tickets': [], 'closed_tickets': 0}
                    elif role.lower() == 'dev':
                        self.config['dev_members'].append(username)
                    else:
                        await message.channel.send("Неправильная роль. Пишите 'staff' или 'dev'.")
                    with open(self.config_file, 'w') as f:
                        json.dump(self.config, f, indent=4)
                    await message.channel.send(f"Добавлена у `{username}` роль: `{role}`")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте $add_rights <username> <role>")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$del_rights'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) == 3:
                    username = args[1]
                    role = args[2]
                    if role.lower() == 'staff':
                        if username in self.config['staff_members']:
                            del self.config['staff_members'][username]
                        else:
                            await message.channel.send(f"{username} нету в staff_member списке.")
                    elif role.lower() == 'dev':
                        if username in self.dev_members:
                            self.dev_members.remove(username)
                        else:
                            await message.channel.send(f"{username} нету в dev_members списке.")
                    else:
                        await message.channel.send("Неправильная роль. Пишите 'staff' или 'dev'.")
                    with open(self.config_file, 'w') as f:
                        json.dump(self.config, f, indent=4)
                    await message.channel.send(f"Убрана у `{username}` роль `{role}`")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте $del_rights <username> <role>")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$add_staff_role'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 2:
                    role_id = args[1]
                    try:
                        role_id = int(role_id)
                        bot.config['staff_roles'].append(role_id)
                        with open(bot.config_file, 'w') as f:
                            json.dump(bot.config, f, indent=4, )
                        await message.channel.send(f"Роль айди: `{role_id}` была добавлена к staff_roles.")
                    except ValueError:
                        await message.channel.send("Неправильная айди роли. Введите правильный айди.")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$add_staff_role <role_id>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$del_staff_role'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 2:
                    role_id = args[1]
                    try:
                        role_id = int(role_id)
                        if role_id in bot.config['staff_roles']:
                            bot.config['staff_roles'].remove(role_id)
                            with open(bot.config_file, 'w') as f:
                                json.dump(bot.config, f, indent=4, )
                            await message.channel.send(f"Роль айди: `{role_id}` была убрана из staff_roles")
                        else:
                            await message.channel.send(f"Роль айди: `{role_id}` не находится в staff_roles")
                    except ValueError:
                        await message.channel.send("Неправильная айди роли. Введите правильный айди.")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$del_staff_role <role_id>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$info'):
            await message.delete()
            if message.author.name.lower() in bot.staff_members:
                staff_members = bot.config.get('staff_members', {})
                sorted_staff_members = sorted(staff_members.items(), key=lambda x: x[1].get('closed_tickets', 0), reverse=True)
                embed = disnake.Embed(
                    title="Информация про бота",
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                embed.add_field(name="Версия ЮТика", value=version, inline=False)
                embed.add_field(name="Всего тикетов", value=f"{bot.ticket_counter}", inline=False)
                embed.add_field(name="Время работы", value=f"{bot.config.get('primetime', {}).get('start', 'Unknown')} - {bot.config.get('primetime', {}).get('end', 'Unknown')}", inline=False)
                embed.add_field(name="Активных тикетов", value=f"{len([channel for channel in bot.get_all_channels() if 'ticket' in channel.name.lower()])}", inline=False)
                embed.set_footer(
                    text="maded by anarchowitz ",
                    icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для staff_members")

        if message.content.startswith('$list_rights'):
            await message.delete()
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                staff_members = bot.config.get('staff_members', {})
                dev_members = bot.config.get('dev_members', [])
                embed = disnake.Embed(
                    title="Список прав доступа",
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                embed.add_field(name="Staff Members", value='\n'.join(staff_members.keys()), inline=False)
                embed.add_field(name="Dev Members", value='\n'.join(dev_members), inline=False)
                embed.set_footer(
                    text="maded by anarchowitz ",
                    icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для staff_members!")

        if message.content.startswith('$list_helper'):
            await message.delete()
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                staff_members = bot.config.get('staff_members', {})
                dev_members = bot.config.get('dev_members', [])
                embed = disnake.Embed(
                    title="Список быстрых ответов",
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                embed.add_field(
                    name="`.скинрейв`",
                    value="Форма выдачи токенов за регистрацию на скинрейве",
                    inline=False
                )
                embed.add_field(
                    name="`.жалоба`",
                    value="Форма о том, что жалоба передана в админ чат",
                    inline=False
                )
                embed.add_field(
                    name="`.коины`",
                    value="Форма о том, что делать с токенами",
                    inline=False
                )
                embed.add_field(
                    name="`.соцсети`",
                    value="Форма о наших соцсетях",
                    inline=False
                )
                embed.add_field(
                    name="`.промоввод`",
                    value="Форма о том, как ввести промокод.",
                    inline=False
                )
                embed.add_field(
                    name="`.блекджек`",
                    value="Форма о том, как играть в блекджек.",
                    inline=False
                )
                embed.set_footer(
                    text="maded by anarchowitz ",
                    icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для staff_members!")   
            
        
        if message.content.startswith('$date_set_stats'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 4:
                    date_str = args[1]
                    staff_member = args[2].lower()
                    closed_tickets = int(args[3])
                    if date_str == 'all' and staff_member == 'all':
                        for date_key in bot.config.get('date_stats', {}).keys():
                            bot.config['date_stats'][date_key] = {k: closed_tickets for k in bot.config['staff_members']}
                    elif date_str == 'all':
                        for date_key in bot.config.get('date_stats', {}).keys():
                            if staff_member in bot.config['staff_members']:
                                bot.config['date_stats'][date_key][staff_member] = closed_tickets
                    elif staff_member == 'all':
                        if date_str in bot.config.get('date_stats', {}):
                            bot.config['date_stats'][date_str] = {k: closed_tickets for k in bot.config['staff_members']}
                        else:
                            bot.config['date_stats'][date_str] = {k: closed_tickets for k in bot.config['staff_members']}
                    else:
                        date_obj = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
                        date_str = date_obj.isoformat()
                        if date_str in bot.config.get('date_stats', {}):
                            bot.config['date_stats'][date_str][staff_member] = closed_tickets
                        else:
                            bot.config['date_stats'][date_str] = {staff_member: closed_tickets}
                    with open(bot.config_file, 'w') as f:
                        json.dump(bot.config, f, indent=4)
                    await message.channel.send(f"Для `{staff_member}` в дату: `{date_str}` было установлено закрытых тикетов {closed_tickets}.")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$date_set_stats <date/all> <staff_member/all> <closed_tickets>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$date_stats'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 2:
                    date_str = args[1]
                    try:
                        date_obj = datetime.datetime.strptime(date_str, '%d.%m.%Y').date()
                        date_str = date_obj.isoformat()
                        if date_str in bot.config.get('date_stats', {}):
                            date_stats = bot.config['date_stats'][date_str]
                            sorted_date_stats = sorted(date_stats.items(), key=lambda x: x[1], reverse=True)
                            embed = disnake.Embed(
                                title=f"Статистика закрытых тикетов за `{date_str}`",
                                color=disnake.Color.from_rgb(119, 137, 253)
                            )
                            for staff_member, closed_tickets in sorted_date_stats:
                                embed.add_field(name=f"`{staff_member}`", value=f"Закрытых тикетов: {closed_tickets}", inline=False)
                            embed.set_footer(
                                text="maded by anarchowitz ",
                                icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                            )
                            await message.channel.send(embed=embed)
                        else:
                            await message.channel.send(f"Нет статистики для даты `{date_str}`")
                    except ValueError:
                        await message.channel.send("Неправильный формат даты. Используйте DD.MM.YYYY")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$date_stats <date>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$stats'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                staff_members = bot.config.get('staff_members', {})
                sorted_staff_members = sorted(staff_members.items(), key=lambda x: x[1].get('closed_tickets', 0), reverse=True)
                embed = disnake.Embed(
                    title="Общая статистика закрытых тикетов",
                    color=disnake.Color.from_rgb(119, 137, 253)
                )
                for i, (staff_member, stats) in enumerate(sorted_staff_members):
                    closed_tickets = stats.get('closed_tickets', 0)
                    embed.add_field(name=f"Топ {i+1}: `{staff_member}`", value=f"", inline=False) #Закрытых тикетов: {closed_tickets}
                embed.set_footer(
                    text="maded by anarchowitz ",
                    icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                )
                await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$secret_stats'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 2:
                    staff_member = args[1].lower()
                    staff_members = bot.config.get('staff_members', {})
                    if staff_member in staff_members:
                        stats = staff_members[staff_member]
                        closed_tickets = stats.get('closed_tickets', 0)
                        embed = disnake.Embed(
                            title=f"Статистика закрытых тикетов для {staff_member}",
                            color=disnake.Color.from_rgb(119, 137, 253)
                        )
                        embed.add_field(name="Закрытых тикетов", value=f"{closed_tickets}", inline=False)
                        embed.set_footer(
                            text="maded by anarchowitz ",
                            icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                        )
                        await message.channel.send(embed=embed)
                    else:
                        await message.channel.send(f"`{staff_member}` не из списка staff_member")
                else:
                    staff_members = bot.config.get('staff_members', {})
                    sorted_staff_members = sorted(staff_members.items(), key=lambda x: x[1].get('closed_tickets', 0), reverse=True)
                    embed = disnake.Embed(
                        title="Общая статистика закрытых тикетов",
                        color=disnake.Color.from_rgb(119, 137, 253)
                    )
                    for i, (staff_member, stats) in enumerate(sorted_staff_members):
                        closed_tickets = stats.get('closed_tickets', 0)
                        embed.add_field(name=f"Топ {i+1}: `{staff_member}`", value=f"Закрытых тикетов: {closed_tickets}", inline=False)
                    embed.set_footer(
                        text="maded by anarchowitz ",
                        icon_url="https://downloader.disk.yandex.ru/preview/8586ae24eff4bf398f634c0eff314ec7517af6a6a6deabc91cac17081b13a333/66e4bb04/-5JA7Y5I4iDB54IFTeoxskulIkFgBGQy35tOihIxLa_lWLqntn--ajaXr1vqzORamh1ZEpIyP0x2BlZcItek1A%3D%3D?uid=0&filename=fc4cd000b95dfcb37a5467ff6f15638b.webp&disposition=inline&hash=&limit=0&content_type=image%2Fjpeg&owner_uid=0&tknv=v2&size=2048x2048",
                    )
                    await message.channel.send(embed=embed)
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$primetime'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) == 3:
                    start_time = args[1]
                    end_time = args[2]
                    self.config['primetime'] = {'start': start_time, 'end': end_time}
                    with open(self.config_file, 'w') as f:
                        json.dump(self.config, f, indent=4)
                    await message.channel.send(f"Рабочее время установлено: `{start_time}` - `{end_time}`")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте $primetime `<start_time>` `<end_time>`\n (e.g $primetime 10:00 20:00)")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$tickets_num'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 2:
                    try:
                        ticket_counter = int(args[1])
                        bot.config['ticket_counter'] = ticket_counter
                        with open(bot.config_file, 'w') as f:
                            json.dump(bot.config, f)
                        await message.channel.send(f"Значение созданных было установленно в значение: `{ticket_counter}`.")
                    except ValueError:
                        await message.channel.send("Неправильное количество. (no int)")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$tickets_num <ticket_counter>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$set'):
            await message.delete()
            if message.author.name.lower() in bot.dev_members:
                args = message.content.split()
                if len(args) == 3:
                    staff_member = args[1]
                    try:
                        closed_tickets = int(args[2])
                        staff_members = bot.config.get('staff_members', {})
                        if staff_member.lower() == 'all':
                            for member in staff_members:
                                staff_members[member]['closed_tickets'] = closed_tickets
                        elif staff_member.lower() in [member.lower() for member in staff_members]:
                            staff_members[staff_member.lower()]['closed_tickets'] = closed_tickets
                            bot.config['staff_members'] = staff_members
                            with open(bot.config_file, 'w') as f:
                                json.dump(bot.config, f)
                            await message.channel.send(f"Установленно для `{staff_member}` в значение `{closed_tickets}`")
                        else:
                            await message.channel.send(f"{staff_member} не из списка staff_member")
                    except ValueError:
                        await message.channel.send("Неправильное количество. (no int)")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$set <staff_member> <closed_tickets>` или `$set all <closed_tickets>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$sum'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) == 3:
                    staff_member = args[1].lower()
                    operation = args[2]
                    staff_members = self.config.get('staff_members', {})
                    if staff_member in staff_members:
                        try:
                            value = int(operation)
                            staff_members[staff_member]['closed_tickets'] += value
                            self.config['staff_members'] = staff_members
                            with open(self.config_file, 'w') as f:
                                json.dump(self.config, f, indent=4)
                            await message.channel.send(f"Успешно изменено значение для `{staff_member}` на `{operation}`")
                        except ValueError:
                            await message.channel.send("Неправильная операция. Используйте **целое** число")
                    else:
                        await message.channel.send(f"`{staff_member}` не из списка staff_member")
                else:
                    await message.channel.send("Неправильный синтаксис. Используйте `$sum <staff_member> <+число/-число>`")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$config_clear'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) > 1:
                    user = args[1].lower()
                    if user == 'all':
                        await message.channel.send(self.config_clear())
                    else:
                        await message.channel.send(self.config_clear(user))
                else:
                    await message.channel.send("Укажите пользователя или `all`, чтобы очистить `claimed_tickets | claimed_ticket_users` и пользователей.")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$clear_tickets'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                args = message.content.split()
                if len(args) > 1:
                    user = args[1].lower()
                    if user == 'all':
                        with open('created_tickets.json', 'w') as f:
                            json.dump({}, f)
                        await message.channel.send("Файл `created_tickets.json` очищен полностью.")
                    else:
                        with open('created_tickets.json', 'r+') as f:
                            try:
                                created_tickets = json.load(f)
                            except json.JSONDecodeError:
                                created_tickets = {}
                            if user in created_tickets:
                                del created_tickets[user]
                                f.seek(0)
                                json.dump(created_tickets, f)
                                f.truncate()
                                await message.channel.send(f"Запись пользователя `{user}` удалена из `created_tickets.json`.")
                            else:
                                await message.channel.send(f"Пользователь `{user}` не найден в `created_tickets.json`.")
                else:
                    await message.channel.send("Укажите ник пользователя или `all`, чтобы очистить `created_tickets.json`.")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$qa_on'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                self.qa_enabled = True
                self.config['qa_enabled'] = True
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                await message.channel.send("Авто-ответчик включен!")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")

        if message.content.startswith('$qa_off'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                self.qa_enabled = False
                self.config['qa_enabled'] = False
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                await message.channel.send("Авто-ответчик выключен!")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content.startswith('$config_date_clear'):
            await message.delete()
            if message.author.name.lower() in self.dev_members:
                self.config['date_stats'] = {}
                with open(self.config_file, 'w') as f:
                    json.dump(self.config, f, indent=4)
                await message.channel.send("Даты в date_stats были успешно очищены.")
            else:
                await message.channel.send("Эта команда доступна только для разработчиков!")
        
        if message.content not in self.qa_pairs and self.qa_enabled and message.channel.id:
            if "ticket" in message.channel.name.lower():
                channel_name = message.channel.name
                staff_member_name = None
                if '-' in channel_name:
                    parts = channel_name.split('-')
                    staff_member_name = parts[0]

                if staff_member_name and staff_member_name in self.config.get('staff_members', {}):
                    return

                if message.author.name.lower() not in self.config.get('staff_members', {}):
                    question = message.content.strip().lower().rstrip('?')
                    possible_questions = list(self.qa_pairs.keys())
                    best_match = max(possible_questions, key=lambda x: difflib.SequenceMatcher(None, x, question).ratio())
                    if difflib.SequenceMatcher(None, best_match, question).ratio() > 0.6:
                        answer = self.qa_pairs[best_match]
                        await message.channel.send(answer)
                    else:
                        pass
                else:
                    pass
            else:
                pass
        
#фаст ансверс биндс
        if message.content.startswith('.скинрейв'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f"Что бы мы вам помогли, уточните.\n1) Как давно вы зарегистрировались на SkinRave?\n2) Авторизировались ли вы под своим Steam аккаунтом?\n3) Ссылка на ваш аккаунт на сайте (yooma.su)\n4) Скриншот профиля на SkinRave. \n\n-# Отправил - {message.author.name}")
            else:
                pass

        if message.content.startswith('.жалоба'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f"Спасибо! Передали ваше обращение Администрации! \n\n-# Отправил - {message.author.name}")
            else:
                pass

        if message.content.startswith('.коины'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f"Коины используются на серверах.\nДля того чтобы их потратить используйте команду !shop на любом сервере проекта. \n\n-# Отправил - {message.author.name}")
            else:
                pass
        
        if message.content.startswith('.соцсети'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f"Все ссылки на наши актуальные соц. сети:\n\nDiscord: <https://ds.yooma.su>\nTelegram: <https://t.me/yoomasu>\nВКонтакте: <https://vk.com/yoomasu>\n\n-# Отправил - {message.author.name}")
            else:
                pass
        
        if message.content.startswith('.промоввод'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f'Для того чтобы активировать промокод, вам нужно нажать на свою аватарку в правом верхнем углу сайта и выбрать "ввести промокод".\n\n-# Отправил - {message.author.name}')
            else:
                pass
        
        if message.content.startswith('.блекджек'):
            if message.author.name.lower() in bot.config.get('staff_members', {}):
                await message.delete()
                await message.channel.send(f'Чтобы открыть игру, вам нужно написать команду !bj в чат игры на сервере\nПоcле этого в чате появится ссылка на игру. Вам необходимо выделить ее мышкой и нажать ПКМ, затем "Копировать выделенный текст".\nДалее зайти в обычный браузер (или в Steam браузер) и ввести эту ссылку туда, откроется игра\n\n-# Отправил - {message.author.name}')
            else:
                pass

    async def claim_ticket(self, message):
        user = message.author
        channel = message.channel
        self.ticket_counter += 1

        with open(self.config_file, 'w') as f:
            self.config['ticket_counter'] = self.ticket_counter
            json.dump(self.config, f, indent=4)

        ticket_channel = message.channel
        await ticket_channel.edit(name=f"{user.name.lower()}-ticket-{ticket_channel.name.split('-')[-1]}")

        staff_members = self.config.get('staff_members', {})
        staff_members[user.name.lower()]['claimed_tickets'] = staff_members[user.name.lower()].get('claimed_tickets', []) + [ticket_channel.id]
        staff_members[user.name.lower()]['claimed_ticket_users'] = staff_members[user.name.lower()].get('claimed_ticket_users', {})
        staff_members[user.name.lower()]['claimed_ticket_users'][ticket_channel.id] = user.name.lower()
        self.config['staff_members'] = staff_members
        with open(self.config_file, 'w') as f:
            json.dump({str(k): v for k, v in self.config.items()}, f, indent=4, )

        info_embed = disnake.Embed(
            description=f"Успешно взялся за тикет - {user.mention}",
            color=disnake.Color.from_rgb(251, 254, 50)
        )
        await ticket_channel.send(embed=info_embed)

    async def close_ticket(self, message):  
        channel = message.channel
        user = message.author
        if "ticket" not in channel.name.lower():
            await message.channel.send("Эта команда доступна только в каналах с названием содержащим слово 'ticket'!")
            return
        staff_members = self.config.get('staff_members', {})
        ticket_claimer = None
        for staff_member, stats in staff_members.items():
            if channel.id in stats.get('claimed_tickets', []):
                ticket_claimer = staff_member
                break
        if ticket_claimer:
            staff_members[ticket_claimer]['closed_tickets'] = staff_members[ticket_claimer].get('closed_tickets', 0) + 1
            self.config['staff_members'] = staff_members
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)

            current_date = datetime.date.today().isoformat()
            if current_date not in self.config.get('date_stats', {}):
                self.config['date_stats'][current_date] = {}
            self.config['date_stats'][current_date][ticket_claimer] = self.config['date_stats'][current_date].get(ticket_claimer, 0) + 1
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)

            embed1 = disnake.Embed(
                description=f"Тикет был закрыт - {user.mention}",
                color=disnake.Color.from_rgb(251, 254, 50)
            )
            embed2 = disnake.Embed(
                description=f"Тикет будет удален через несколько секунд",
                color=disnake.Color.from_rgb(239, 82, 80)
            )
            await channel.send(embed=embed1)
            await channel.send(embed=embed2)
            await asyncio.sleep(4)
            await channel.delete()

    async def on_interaction(self, interaction: disnake.Interaction):
        if interaction.type == disnake.InteractionType.component:
            if interaction.data.custom_id == 'create_ticket':
                await self.create_ticket(interaction)
    
    async def create_ticket(self, interaction: disnake.Interaction):
        await interaction.response.defer()
        creating_ticket_msg = await interaction.followup.send(f"Cоздаю тикет...", ephemeral=True)
        user = interaction.user
        guild = interaction.guild
        category = guild.get_channel(self.CATEGORY_ID)

        self.ticket_counter += 1

        with open('created_tickets.json', 'r+') as f:
            try:
                created_tickets = json.load(f)
            except json.JSONDecodeError:
                created_tickets = {}

            if interaction.user.name in created_tickets:
                await creating_ticket_msg.edit("Вы уже создали тикет. Ждите ответа от нашего персонала.")
                return

            created_tickets[interaction.user.name] = True
            f.seek(0)
            json.dump(created_tickets, f)
            f.truncate()
        
        with open(self.config_file, 'w') as f:
            self.config['ticket_counter'] = self.ticket_counter
            json.dump(self.config, f, indent=4)

        ticket_channel = await category.create_text_channel(f"ticket-{self.ticket_counter}")
        await ticket_channel.set_permissions(guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(user, read_messages=True, send_messages=True)

        staff_roles = self.config.get('staff_roles', [])
        for role_id in staff_roles:
            role = guild.get_role(role_id)
            if role:
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)

        embed = disnake.Embed(
            title="Служба поддержки свяжется с вами в **ближайшее время**",
            description=f"Чтобы закрыть этот запрос, нажмите на кнопку 🔒 **Закрыть**",
            color=disnake.Color.from_rgb(119, 137, 253)
        )
        embed.set_footer(
            text="YooTick - the best solution ",
            icon_url="https://sun1-92.userapi.com/s/v1/ig2/G9o3wAE5UNHK5XP1ExY3xxkI3tpSADzi7m0Of5hWJZ64R0dmho6jjjp-irvh3CypEQ26lfGN1AS0kay1cw-EtXFb.jpg?size=1500x1500&quality=95&crop=0,0,1500,1500&ava=1",
        )
        view = ButtonView()
        take_ticket_button = disnake.ui.Button(label='Взять тикет', style=disnake.ButtonStyle.blurple, emoji='📝')
        close_ticket_button = disnake.ui.Button(label='Закрыть тикет', style=disnake.ButtonStyle.red, emoji='🔒')
        view.add_item(take_ticket_button)
        view.add_item(close_ticket_button)

        await ticket_channel.send(f"{user.mention}, ваш тикет создан!", embed=embed, view=view)
        current_time = datetime.datetime.now()
        primetime = self.config.get('primetime')
        if primetime:
            start_time = datetime.datetime.strptime(primetime['start'], '%H:%M').time()
            end_time = datetime.datetime.strptime(primetime['end'], '%H:%M').time()
            if start_time <= current_time.time() <= end_time:
                pass
            else:
                await ticket_channel.send(f"{interaction.user.mention}, В данный момент нерабочее время, и время ответа может занять больше времени, чем обычно.\nПожалуйста, оставайтесь на связи, и мы ответим вам, как только сможем.")
        else:
            pass    
        await creating_ticket_msg.edit(f"Ваш тикет был создан - {ticket_channel.mention}")

        async def take_ticket_callback(interaction: disnake.Interaction):
            user = interaction.user
            staff_members = bot.config.get('staff_members', {})
            if user.name.lower() in staff_members:
                ticket_channel = interaction.channel
                await ticket_channel.edit(name=f"{user.name.lower()}-ticket-{ticket_channel.name.split('-')[-1]}")

                staff_members[user.name.lower()]['claimed_tickets'] = staff_members[user.name.lower()].get('claimed_tickets', []) + [ticket_channel.id]
                bot.config['staff_members'] = staff_members
                with open(bot.config_file, 'w') as f:
                    json.dump(bot.config, f, indent=4)

                info_embed = disnake.Embed(
                    description=f"Успешно взялся за тикет - {user.mention}",
                    color=disnake.Color.from_rgb(251, 254, 50)
                )
                await ticket_channel.send(embed=info_embed)
                await interaction.response.defer()
            else:
                await interaction.response.send_message("У вас нет прав для совершение данного действия.", ephemeral=True)

        async def close_ticket_callback(interaction: disnake.Interaction):
            ticket_channel = interaction.channel
            user = interaction.user

            channel_name = ticket_channel.name
            staff_member_name = None
            if '-' in channel_name:
                parts = channel_name.split('-')
                staff_member_name = parts[0]

            confirmation_embed = disnake.Embed(
                title="Подтверждение",
                description="Вы уверены что хотите закрыть тикет?",
                color=disnake.Color.from_rgb(119, 137, 253)
            )

            view = ButtonView()

            view.clear_items()

            button_close = disnake.ui.Button(label='Закрыть', style=disnake.ButtonStyle.red, emoji='🔒')
            button_cancel = disnake.ui.Button(label='Отмена', style=disnake.ButtonStyle.gray, emoji='🚫')
            view.add_item(button_close)
            view.add_item(button_cancel)

            await interaction.response.send_message(embed=confirmation_embed, view=view)

            async def close_callback(interaction: disnake.Interaction):
                channel = interaction.channel
                user = interaction.user
                staff_members = bot.config.get('staff_members', {})

                ticket_claimer = None
                for staff_member, stats in staff_members.items():
                    if channel.id in stats.get('claimed_tickets', []):
                        ticket_claimer = staff_member
                        break

                if ticket_claimer:
                    staff_members[ticket_claimer]['claimed_tickets'].remove(channel.id)

                    staff_members[ticket_claimer]['closed_tickets'] = staff_members[ticket_claimer].get('closed_tickets', 0) + 1
                    bot.config['staff_members'] = staff_members
                    with open(bot.config_file, 'w') as f:
                        json.dump(bot.config, f)

                    current_date = datetime.date.today().isoformat()
                    if current_date not in bot.config.get('date_stats', {}):
                        bot.config['date_stats'][current_date] = {}
                    bot.config['date_stats'][current_date][ticket_claimer] = bot.config['date_stats'][current_date].get(ticket_claimer, 0) + 1
                    with open(bot.config_file, 'w') as f:
                        json.dump(bot.config, f)

                    with open(bot.config_file, 'r') as f:
                        config = json.load(f)
                    config['ticket_counter'] -= 1
                    with open(bot.config_file, 'w') as f:
                        json.dump(config, f)

                embed1 = disnake.Embed(
                    description=f"Тикет был закрыт - {user.mention}",
                    color=disnake.Color.from_rgb(251, 254, 50)
                )
                embed2 = disnake.Embed(
                    description=f"Тикет будет удален через несколько секунд",
                    color=disnake.Color.from_rgb(239, 82, 80)
                )
                with open('created_tickets.json', 'r+') as f:
                    try:
                        created_tickets = json.load(f)
                    except json.JSONDecodeError:
                        created_tickets = {}

                    if interaction.user.name in created_tickets:
                        del created_tickets[interaction.user.name]
                        f.seek(0)
                        json.dump(created_tickets, f)
                        f.truncate()
                await interaction.response.defer()
                await interaction.message.delete()
                await channel.send(embed=embed1)
                await channel.send(embed=embed2)
                await asyncio.sleep(4)
                await channel.delete()

            button_close.callback = close_callback

            async def cancel_callback(interaction: disnake.Interaction):
                await interaction.message.delete()

            button_cancel.callback = cancel_callback


        take_ticket_button.callback = take_ticket_callback
        close_ticket_button.callback = close_ticket_callback

bot = PersistentViewBot(activity=disnake.Activity(type=disnake.ActivityType.competing, name="yooma.su"))

if __name__ == "__main__":
    bot.run("YOUR_DISCORD_TOKEN_BOT")
