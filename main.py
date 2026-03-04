import discord
from discord import app_commands
import os
import random
import time

TOKEN = os.getenv("TOKEN")  # ✅ Railway utilisera la variable d'environnement

if not TOKEN:
    raise ValueError("Le TOKEN n'est pas défini dans les variables d'environnement.")

intents = discord.Intents.default()
intents.presences = True
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# --- Configuration ---
CATEGORIES = ["crunchyroll", "xbox", "steam"]
COOLDOWN_TIME = 60  # secondes
REQUIRED_STATUS_KEY = "WMvRYcnKM4"
REQUIRED_ROLE_NAME = "Client"

cooldowns = {}

# ==============================
# Vérification accès utilisateur
# ==============================

async def check_access(interaction: discord.Interaction):
    user = interaction.user
    guild = interaction.guild

    if not guild:
        return False, "❌ Cette commande doit être utilisée dans un serveur."

    member = guild.get_member(user.id)

    if not member:
        return False, "❌ Impossible de vérifier ton rôle."

    role_names = [role.name for role in member.roles]
    if REQUIRED_ROLE_NAME not in role_names:
        return False, f"❌ Tu dois avoir le rôle **{REQUIRED_ROLE_NAME}** pour utiliser le générateur."

    custom_status = None
    for activity in member.activities:
        if isinstance(activity, discord.CustomActivity):
            custom_status = activity.name
            break

    if not custom_status or REQUIRED_STATUS_KEY not in custom_status:
        return False, "❌ Tu dois mettre la clé requise dans ton statut personnalisé."

    return True, None

# ==============================
# Menu Sélection
# ==============================

class AccountSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Crunchyroll", value="crunchyroll"),
            discord.SelectOption(label="Xbox", value="xbox"),
            discord.SelectOption(label="Steam", value="steam"),
        ]
        super().__init__(
            placeholder="Choisis un service",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):

        access, message = await check_access(interaction)
        if not access:
            await interaction.response.send_message(message, ephemeral=True)
            return

        user_id = interaction.user.id
        now = time.time()

        if user_id in cooldowns:
            elapsed = now - cooldowns[user_id]
            if elapsed < COOLDOWN_TIME:
                await interaction.response.send_message(
                    f"⏳ Attends encore {int(COOLDOWN_TIME - elapsed)} secondes.",
                    ephemeral=True
                )
                return

        category = self.values[0]
        file_path = f"comptes/{category}.txt"

        if not os.path.exists(file_path):
            await interaction.response.send_message(
                f"❌ Aucun fichier trouvé pour {category}.",
                ephemeral=True
            )
            return

        with open(file_path, "r", encoding="utf-8") as f:
            accounts = [line.strip() for line in f if line.strip()]

        if not accounts:
            await interaction.response.send_message(
                f"❌ Plus de stock pour {category.upper()}",
                ephemeral=True
            )
            return

        access, message = await check_access(interaction)
        if not access:
            await interaction.response.send_message(message, ephemeral=True)
            return

        account = random.choice(accounts)
        accounts.remove(account)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(accounts))

        cooldowns[user_id] = now

        await interaction.response.send_message(
            f"✅ **Service :** {category.upper()}\n"
            f"📦 **Stock restant :** {len(accounts)}\n\n"
            f"🔑 **Compte :** `{account}`",
            ephemeral=True
        )

class AccountView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AccountSelect())

class MainButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Générer un compte", style=discord.ButtonStyle.green)
    async def generate_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "Choisis une catégorie :",
            view=AccountView(),
            ephemeral=True
        )

    @discord.ui.button(label="Voir le stock", style=discord.ButtonStyle.blurple)
    async def stock_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            title="📦 Stock des comptes disponibles",
            color=discord.Color.blue()
        )

        for category in CATEGORIES:
            file_path = f"comptes/{category}.txt"

            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    accounts = [line.strip() for line in f if line.strip()]
                embed.add_field(name=category.upper(), value=len(accounts), inline=False)
            else:
                embed.add_field(name=category.upper(), value="0", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="menu", description="Ouvre le menu du générateur")
async def menu(interaction: discord.Interaction):
    await interaction.response.send_message(
        "💠 Menu Générateur de comptes",
        view=MainButtons(),
        ephemeral=True
    )

@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Connecté en tant que {client.user}")

client.run(TOKEN)
