import inspect
import random
import sys
import io
import time
import functools

import numpy
import discord
import PIL

from scipy.io import wavfile
from unittest import mock
from io import BytesIO
from urllib.parse import urlsplit
from PIL import ImageFilter, ImageFont, Image, ImageDraw, ImageEnhance, ImageOps
from discord.ext import commands
from jishaku.codeblocks import codeblock_converter
from extensions.external import asciify, kromo, halftone
from extensions.models.exceptions import (
    ImageScriptException, MissingBracketsException, MissingSemicolonException, UnknownOperationException,
    TooMuchToDoException, BadInputException, BadSyntaxException, MissingColonException
)


ROOT_DIRECTORY = f"{sys.path[0]}/".replace("\\", "/")
DOCSTRING_MAPPING = {
    "tunnelvision": "Far away!",
    "glitch": "Ruin an image",
    "colortrast": "Colorizes an image in red/blue light",
    "triangulate": "Fits an image into a cool-looking pattern",
    "stringify": "Make an image look like a joy division album cover",
    "quilt": "Jumbled squares.",
    "mosaic": "Sqaure dance!",
    "halftone": "Fancy depressive dots.",
    "chromatic": "Fancy lens things!",
    "xokify": "xok",
    "jpeg": "Ever wanted to make an image look terrible?",
    "blur": "Blur an image. Everyone has to start somewhere.",
    "fry": "Deep-frying, except not really.",
    "asciify": "Turn an image into some spicy dots.",
    "gay": "Unleash the powers of homosexuality on any image.",
    "bless": "🛐🛐🛐",
    "nom": "Eating is a fun and enjoyable activity.",
    "lapse": "I can't quite remember..."

}


class BanLocation():

    def __init__(self):
        self.x, self.y = random.randint(1, 512), random.randint(1, 512)
        self.vectorx, self.vectory = 0, 0
        self.speed = random.randint(4, 9)

        while self.vectorx == 0 and self.vectory == 0:
            self.vectorx, self.vectory = random.randint(-1, 1), random.randint(-1, 1)

    def update_frame(self):
        self.x += (self.vectorx * self.speed)
        self.y += (self.vectory * self.speed)


class BanConglomerate():

    def __init__(self):
        self.bans = [BanLocation() for _ in range(random.randint(9, 12))]
        self.frames = 0

    def generate_frame(self, banimg):
        img = Image.new("RGBA", (640, 640), (54, 57, 63, 255))

        for x in self.bans:
            img.paste(banimg, (x.x, x.y), banimg)
            x.update_frame()

        if self.frames == 10:
            self.bans.append(BanLocation())
            self.frames = -1

        self.frames += 1

        return img


class Cog(commands.Cog, name="Editing"):
    """Edit images. Almost all commands in this module will take an ``Image`` parameter.

You can either:
- attach the image to the message you send the command in
- @mention a user to use their profile picture
- use a custom emoji
- or pass it using a URL when using the command
If you don't do any of that, Lobstero will search the previous few messages for an image."""

    def __init__(self, bot):
        self.bot = bot
        self.session = bot.session

    async def wrap(self, func, *args, **kwargs):
        """Wraps a sync function into a threadpool'd asynchronous executor."""

        new_func = functools.partial(func, *args, **kwargs)
        output = await self.bot.loop.run_in_executor(None, new_func)

        return output

    def iter_attachments(self, items):
        current = []
        valid = [".jpeg", ".jpg", ".png", ".webp", "gif"]
        for item in items:
            if True not in [str(item.filename).lower().endswith(v) for v in valid]:
                continue

            if item.height:  # actually media
                current.append(item.url)
            else:
                continue

        return [[item, True] for item in current]

    async def package(self, file_loc, download=True):
        """Packages a local or downloaded file into an object."""

        try:
            file_name = urlsplit(file_loc)[2].split('/')[-1]
            file_ext = file_name.split(".", 1)[1]
        except (KeyError, IndexError):
            return None  # Not a well-formed url
        f = io.BytesIO()

        if download:
            try:
                async with self.session.get(file_loc) as resp:
                    f.write(await resp.read())
            except (OSError, ValueError):
                return None
        else:
            try:
                b = open(file_loc, "rb")
                f.write(b.read())
            except (OSError, ValueError):
                return None

        # This should (hopefully) never fail
        f_obj = mock.Mock()
        f_obj.data, f_obj.name, f_obj.ext = f, file_name, file_ext

        return f_obj

    async def process_file(self, ctx, url):
        results = []  # Sequence of [URL / filename: str, downloadable: bool]

        #  1: Try member lookup
        c = commands.MemberConverter()
        try:
            m = await c.convert(ctx, str(url))
        except commands.BadArgument:
            pass
        else:
            results.append([str(m.avatar_url_as(format="png", size=2048)), True])

        # Don't bother with this for now
        # 2: Try emoji lookup
        # em = list(chain(*strings.split_count(str(url))))  # for unicode emoji
        # if em:
        #     escape = "-".join([f"{ord(e):X}" for e in em]).lower()
        #     results.append([f"{ROOT_DIRECTORY}data/static/emojis/{escape}.png", False])

        # 2.5: Try custom emoji lookup
        c = commands.PartialEmojiConverter()
        try:
            e = await c.convert(ctx, str(url))
        except commands.BadArgument:
            pass
        else:
            results.append([str(e.url), True])

        # 3: Try message attachments
        results.extend(self.iter_attachments(ctx.message.attachments))

        # 4: Try as just a URL
        valid = [".jpeg", ".jpg", ".png", ".webp", "gif"]
        if True in [str(url).lower().endswith(v) for v in valid]:
            results.append([str(url), True])

        # 5 & 6: Try looking through embeds and attachments in previous messages
        try:
            messages = await ctx.history(limit=15).flatten()
        except discord.DiscordException:
            messages = []

        for message in messages:
            embed_images = filter(None, [embed.image for embed in message.embeds])
            results.extend(self.iter_attachments(embed_images))
            results.extend(self.iter_attachments(message.attachments))

        # 7: Give up
        results.append([str(ctx.author.avatar_url_as(static_format="png", size=2048)), True])

        # Last step: Attempt to find one that works and return
        for result in results:
            try:
                constructed = await self.package(*result)
            except (OSError, IndexError, ValueError, KeyboardInterrupt):
                pass
            else:
                if not constructed:
                    continue

                constructed.data.seek(0)
                return constructed

        await ctx.send("Congratulations! You've found Arnold, the unreachable code path! Now time will implode.")
        return None

    async def save_and_send(self, ctx, output, name, elapsed=None, *args, **kwargs):
        # Saves an Image into a BytesIO buffer and sends it.
        # Extra args/ kwargs are passed to save.
        file_f = name.split('.')[1]
        buffer = BytesIO()
        output.save(buffer, file_f, *args, **kwargs)
        buffer.seek(0)

        constructed_file = discord.File(fp=buffer, filename=name)
        embed = discord.Embed(color=16202876)
        embed.set_image(url=f"attachment://{name}")
        embed.description = elapsed
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)

        await ctx.send(file=constructed_file, embed=embed)

    async def save_for_next_step(self, ctx, output, name, *args, **kwargs):
        # Saves an Image into a BytesIO buffer. This is an intermediary thing.
        # Extra args/ kwargs are passed to save.
        file_name, file_f = name.split('.')
        buffer = BytesIO()
        output.save(buffer, file_f, *args, **kwargs)
        buffer.seek(0)

        f_obj = mock.Mock()
        f_obj.data, f_obj.name, f_obj.ext = buffer, file_name, file_f

        return f_obj

    async def process_single(self, op, ctx, url):
        result = await self.process_file(ctx, url)
        if result is None:
            return

        to_do = getattr(self, f"image_do_{op}")

        # ugly, will fix later
        try:
            processed = list(await self.wrap(to_do, result))
        except ImageScriptException as e:
            return await ctx.send(str(e))

        if len(processed) == 2:
            processed.append({})

        await self.save_and_send(ctx, processed[0], processed[1], **processed[2])

    async def imagescript_run(self, ctx, input_code, provided_image):
        if not input_code:
            raise ImageScriptException("No code to run!")

        if ";" not in input_code:
            raise MissingSemicolonException("Missing semicolon!")

        start = time.time()
        current_image = provided_image
        chunked_code = input_code.strip("\r\n\u200b.}{][").split(";")
        cleaned_chunks = list(filter(None, chunked_code))

        if len(cleaned_chunks) > 15:
            raise TooMuchToDoException(f"Only 15 operations are allowed at once. You tried to do {len(cleaned_chunks)}")

        for current_step, chunk in enumerate(cleaned_chunks, start=1):
            if not ("(" in chunk or ")" in chunk):
                raise MissingBracketsException("No brackets present!", current_step)

            try:
                function_body, function_args = chunk.strip(") ").split("(")
            except ValueError:
                raise BadSyntaxException("Too many brackets for one operation!", current_step)

            op_to_run = getattr(self, f"image_do_{function_body}", None)
            if op_to_run is None:
                raise UnknownOperationException(f"Operation {function_body} does not exist!", current_step)

            if function_args.strip():
                try:
                    arguments = {arg.split(":")[0]: arg.split(":")[1] for arg in function_args.split(",")}
                except (ValueError, IndexError):
                    raise MissingColonException("No colon to denote argument value!", current_step)
            else:
                arguments = {}

            try:
                arguments = {key: int(value) for key, value in arguments.items()}
            except ValueError:
                raise BadInputException("Argument must be a number, not a word or letter!", current_step)

            try:
                results = await op_to_run(current_image, **arguments)
            except TypeError:
                raise BadInputException(f"Provided arguments are not valid for operation {function_body}", current_step)

            processed = list(results)
            if len(processed) == 2:
                processed.append({})

            if current_step != len(cleaned_chunks):
                current_image = await self.save_for_next_step(ctx, processed[0], processed[1], **processed[2])
            else:
                completion = time.time()
                time_taken = f"Completed {len(cleaned_chunks)} operation(s) in {round(completion - start, 2)} seconds."
                await self.save_and_send(ctx, processed[0], processed[1], elapsed=time_taken, **processed[2])

    def image_do_blur(self, result, amount=10):
        myimage = Image.open(result.data)
        im = myimage.convert("RGBA")
        output = im.filter(ImageFilter.GaussianBlur(amount))

        return output, "blur.png"

    def image_do_gay(self, result):
        simage = Image.open(result.data)
        gim = Image.open(f"{ROOT_DIRECTORY}extensions/data/flag.jpg").convert("RGBA")
        im = simage.convert("RGBA")

        width, height = im.size
        gim_p = gim.resize((width, height), Image.NEAREST)
        output = Image.blend(im, gim_p, 0.5)

        return output, "gay.png"

    def image_do_fry(self, result, amount=2):
        simage = Image.open(result.data)
        im = simage.convert("RGBA")
        output = im.filter(ImageFilter.UnsharpMask(radius=10, percent=450, threshold=amount))

        return output, "fry.png"

    def image_do_nom(self, result):
        d_im = Image.open(result.data).convert("RGBA")

        c_owobase = Image.open(f"{ROOT_DIRECTORY}extensions/data/blob_base.png").convert("RGBA")
        c_owotop = Image.open(f"{ROOT_DIRECTORY}extensions/data/blob_overlay.png").convert("RGBA")

        wpercent = (420 / float(d_im.size[0]))
        hsize = int((float(d_im.size[1]) * float(wpercent)))
        pd_im = d_im.resize((420, hsize), Image.ANTIALIAS)

        width, height = pd_im.size
        offset = (216, 528, 216 + int(width), 528 + int(height))
        offset2 = (0, 0, 1024, 1024)

        c_owobase.paste(pd_im, offset, pd_im)
        c_owobase.paste(c_owotop, offset2, c_owotop)

        return c_owobase, "nom.png"

    def image_do_bless(self, result):
        im = Image.open(result.data).convert("RGBA")
        c_im = im.resize((1024, 1024), PIL.Image.ANTIALIAS)
        c_blesstop = Image.open(f"{ROOT_DIRECTORY}extensions/data/bless.png").convert("RGBA")

        c_im.paste(c_blesstop, (0, 0, 1024, 1024), c_blesstop)

        return c_im, "bless.png"

    def image_do_asciify(self, result):
        opened = Image.open(result.data).convert("RGBA")
        colorlist = [
            "blue", "green", "red", "orange", "greenyellow", "lawngreen", "hotpink",
            "mediumturquoise", "mistyrose", "orangered"]

        bglist = ["black", "black"]
        asciified = asciify.asciiart(
            opened, 0.2, 1.5, ..., str(random.choice(colorlist)),
            str(random.choice(colorlist)), str(random.choice(bglist)))

        return asciified, "ascii.png"

    def image_do_xokify(self, result):
        im = Image.open(result.data).convert("RGBA")
        c_im = im.resize((1024, 1024), PIL.Image.ANTIALIAS)
        converter = ImageEnhance.Color(c_im)
        c_mask = Image.open(f"{ROOT_DIRECTORY}extensions/data/xok_mask.png").convert("RGBA")
        c_xok = Image.open(f"{ROOT_DIRECTORY}extensions/data/xok.png").convert("RGBA")

        converted = converter.enhance(1.75)
        blended = Image.blend(c_xok, converted, 0.3)
        masked = Image.new('RGBA', (1024, 1024))
        masked.paste(blended, (0, 0, 1024, 1024), c_mask)

        return masked, "xok.png"

    def image_do_jpeg(self, result, quality=1):
        d_im = Image.open(result.data).convert("CMYK")
        d_im.thumbnail((200, 200))

        return d_im, "jpegify.jpeg", {"quality": quality}

    def image_do_chromatic(self, result, strength=2):
        d_im = Image.open(result.data).convert("RGB")
        d_im.thumbnail((1024, 1024))
        if (d_im.size[0] % 2 == 0):
            d_im = d_im.crop((0, 0, d_im.size[0] - 1, d_im.size[1]))
            d_im.load()
        if (d_im.size[1] % 2 == 0):
            d_im = d_im.crop((0, 0, d_im.size[0], d_im.size[1] - 1))
            d_im.load()

        final_im = kromo.add_chromatic(d_im, strength=strength, no_blur=True)

        return final_im, "chromatic.png"

    def image_do_halftone(self, result):
        im = Image.open(result.data)
        h = halftone.Halftone()
        output = h.make(im, style='grayscale', angles=[45], sample=16)

        return output, "halftone.png"

    def package_wheel(self, wheel, degrees, ban, ban_mask, banhandler):
        whl = wheel.rotate(degrees)
        whl.paste(ban, None, ban)
        out = banhandler.generate_frame(ban_mask)
        out.paste(whl, (63, 63), whl)
        out.thumbnail((400, 400))

        return out

    def smooth_resize(self, img, basewidth=1000, method=Image.LANCZOS):
        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))

        return img.resize((basewidth, hsize), method)

    def image_do_mosaic(self, result):
        d_im = Image.open(result.data).convert("RGBA")
        base = self.smooth_resize(d_im, 100, Image.NEAREST)
        c_base = base.convert("L").convert("RGBA")
        c_base = self.smooth_resize(d_im, int(base.size[0] / 8), Image.NEAREST)
        overlay = self.smooth_resize(base, base.size[0] * 10, Image.NEAREST)
        canvas = Image.new("RGBA", (overlay.size[0], overlay.size[1]))

        for w_pos in range(0, overlay.size[0] + 1, c_base.size[0]):
            for h_pos in range(0, overlay.size[1] + 1, c_base.size[1]):
                canvas.paste(c_base, (w_pos, h_pos), c_base)

        canvas = canvas.convert("L").convert("RGBA")
        output = Image.blend(canvas, overlay, 0.3)

        return output, "mosaic.png"

    def image_do_quilt(self, result, squares="random"):
        im = Image.open(result.data).convert("RGBA")
        im.thumbnail((4000, 4000))
        width, height = im.size
        if width <= 50 or height <= 50:
            raise BadInputException("Image too small!")

        if squares == "random":
            divisor = random.choice([2, 4, 5, 10])
        else:
            if squares not in [2, 4, 5, 10]:
                raise BadInputException(f"Squares value must be either 2, 4, 5 or 10. {squares} provided.")
            divisor = squares

        new_im = im.resize((round(width, -1), round(height, -1)))
        width, height = new_im.size
        canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        width, height = int(width / divisor), int(height / divisor)
        positions = []

        for x in range(0, width * divisor, width):
            for y in range(0, height * divisor, height):
                dimensions = (x, y, x + width, y + height)
                positions.append(new_im.crop(dimensions))

        random.shuffle(positions)
        counter = 0
        for x in range(0, width * divisor, width):
            for y in range(0, height * divisor, height):
                canvas.paste(positions[counter], (x, y))
                counter += 1

        return canvas, "quilt.png"

    def make_meme(self, topString, bottomString, filename):
        img = Image.open(filename).convert("RGBA")

        wpercent = (2048/float(img.size[0]))
        hsize = int((float(img.size[1])*float(wpercent)))
        img = img.resize((2048, hsize), Image.ANTIALIAS)

        imageSize = img.size

        # find biggest font size that works
        fontSize = int(imageSize[1]/5)
        font = ImageFont.truetype(f"{ROOT_DIRECTORY}extensions/data/impact.ttf", fontSize)
        topTextSize = font.getsize(topString)
        bottomTextSize = font.getsize(bottomString)
        while topTextSize[0] > imageSize[0]-20 or bottomTextSize[0] > imageSize[0]-20:
            fontSize = fontSize - 1
            font = ImageFont.truetype(f"{ROOT_DIRECTORY}extensions/data/impact.ttf", fontSize)
            topTextSize = font.getsize(topString)
            bottomTextSize = font.getsize(bottomString)

        # find top centered position for top text
        topTextPositionX = (imageSize[0]/2) - (topTextSize[0]/2)
        topTextPositionY = 0
        topTextPosition = (topTextPositionX, topTextPositionY)

        # find bottom centered position for bottom text
        bottomTextPositionX = (imageSize[0]/2) - (bottomTextSize[0]/2)
        bottomTextPositionY = imageSize[1] - bottomTextSize[1]
        bottomTextPosition = (bottomTextPositionX, bottomTextPositionY)

        draw = ImageDraw.Draw(img)
        for x_p in range(-15, 15, 5):
            for y_p in range(-15, 15, 5):
                draw.text((topTextPositionX + x_p, topTextPositionY + y_p), topString, (0, 0, 0), font=font)
                draw.text((bottomTextPositionX + x_p, bottomTextPositionY + y_p), topString, (0, 0, 0), font=font)

        draw.text(topTextPosition, topString, (255, 255, 255), font=font)
        draw.text(bottomTextPosition, bottomString, (255, 255, 255), font=font)

        return img

    def image_do_triangulate(self, result):
        im = Image.open(result.data).convert("RGBA")
        if im.size[0] < 20 or im.size[1] < 20:
            raise BadInputException("Image too small!")

        im.thumbnail((20, 20))
        width, height = im.size
        canvas = Image.new("RGBA", (width * 20, height * 20), (0, 0, 0, 0))
        arr = numpy.array(im)
        draw = ImageDraw.Draw(canvas)

        every_first = arr[::1, ::1]
        every_second = arr[1::1, 1::1]

        for row_index, (row1, row2) in enumerate(zip(every_first, every_second)):
            for column_index, (color1, color2) in enumerate(zip(row1, row2)):
                color1 = tuple(color1)  # fuck numpy
                color2 = tuple(color2)  # PIL too

                draw.polygon(
                    (
                        (row_index * 20, column_index * 20 + 20),  # bottom left
                        (row_index * 20, column_index * 20),  # top left
                        (row_index * 20 + 20, column_index * 20)  # top right
                    ),
                    fill=color1)

                draw.polygon(
                    (
                        (row_index * 20, column_index * 20 + 20),  # bottom left
                        (row_index * 20 + 20, column_index * 20 + 20),  # bottom right
                        (row_index * 20 + 20, column_index * 20)  # top right
                    ),
                    fill=color2)

        output = canvas.rotate(-90).transpose(Image.FLIP_LEFT_RIGHT)
        return output, "triangulate.png"

    def image_do_stringify(self, result, invert=False):
        im = Image.open(result.data).convert("L")
        if im.size[0] < 50 or im.size[1] < 50:
            raise BadInputException("Image too small!")
        if invert:
            im = ImageOps.invert(im)

        im.thumbnail((50, 50))
        brightest = int((sorted(numpy.array(im).flatten(), reverse=True)[0] / 255) * 100)
        width, height = im.size
        canvas = Image.new("L", (width * 100 - 100, height * 100))
        arr = numpy.flipud(numpy.rot90(numpy.array(im)))
        draw = ImageDraw.Draw(canvas)

        every_first = arr[::1, ::1]
        every_second = arr[1::1, ::1]

        for row_index, (row1, row2) in enumerate(zip(every_first, every_second)):
            for column_index, (color1, color2) in enumerate(zip(row1, row2)):
                height1 = 2 * ((int((color1 / 255) * 100) * 100) / brightest)
                height2 = 2 * ((int((color2 / 255) * 100) * 100) / brightest)

                draw.polygon(
                    (
                        (row_index * 100, column_index * 100 + 100),
                        (row_index * 100, column_index * 100 + height1),
                        (row_index * 100 + 100, column_index * 100 + height2),
                        (row_index * 100 + 100, column_index * 100 + 100)
                    ),
                    fill="black")

                for offset in range(3):
                    draw.line(
                        (
                            (row_index * 100, column_index * 100 + height1 + offset * 3),
                            (row_index * 100 + 100, column_index * 100 + height2 + offset * 3)
                        ),
                        fill="white", width=12, joint="curve")

        return canvas, "stringify.png"

    def image_do_colortrast(self, result, invert=False):
        im = Image.open(result.data).convert("L")
        if invert:
            im = ImageOps.invert(im)

        output = ImageOps.colorize(im, "DodgerBlue", "FireBrick", "FloralWhite")

        return output, "colortrast.png"

    def image_do_glitch(self, result, max_times=40):
        im = Image.open(result.data).convert("RGB")
        for _ in range(random.randint(20, max_times)):
            random_slice_y = random.randint(1, im.size[1] - 1)
            sliced = im.crop((0, random_slice_y, im.size[0], random_slice_y + 1))
            starting_position = random.randint(1, im.size[1] - 1)

            for i in range(random.randint(12, 20)):
                im.paste(sliced, (0, starting_position + i))

        return im, "glitch.png"

    def image_do_tunnelvision(self, result):
        im = Image.open(result.data).convert("RGB")
        for i, _ in enumerate(range(random.randint(30, 60))):
            m = float(f"0.{100 - i}")
            new_x = int(im.size[0] * m)
            new_y = int(im.size[1] * m)

            to_stamp = im.resize((new_x, new_y))
            position = (
                int(im.size[0] / 2 - to_stamp.size[0] / 2) + random.randint(-3, 3),
                int(im.size[1] / 2 - to_stamp.size[1] / 2) + random.randint(-3, 3)
            )

            im.paste(to_stamp, position)

        return im, "tunnel.png"

    def _generate_blot(self, radius):
        canvas = Image.new("RGBA", (radius * 2, radius * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((0, 0, radius * 2, radius * 2), (255, 255, 255, 255))
        expanded = ImageOps.expand(canvas, radius)
        blurred = expanded.filter(ImageFilter.BoxBlur(radius / 9.5))

        return blurred

    def image_do_lapse(self, result):
        base = Image.open(result.data).convert("RGBA")
        average = int((base.size[0] + base.size[1]) / 2)
        new = base.copy()

        for _ in range(random.randint(160, 200)):
            radius = random.randint(int(average / 30), int(average / 5))
            blot = self._generate_blot(radius)

            random_x = random.randint(radius, base.size[0] - radius)
            random_y = random.randint(radius, base.size[1] - radius)

            chunk = base.crop((random_x, random_y, random_x + radius * 2, random_y + radius * 2))
            expanded_chunk = ImageOps.expand(chunk, radius)

            new_random_x = random.randint(0, base.size[0])
            new_random_y = random.randint(0, base.size[1])

            new.paste(expanded_chunk, (new_random_x, new_random_y), blot)

        return new, "lapse.png"

    @commands.command()
    async def shitpost(self, ctx, *, url=None):
        """It's humour from the future!"""

        result = await self.process_file(ctx, url)
        if result is None:
            return

        markov = await self.bot.markov_generator.generate()
        meme = self.make_meme(markov, markov, result.data)

        await self.save_and_send(ctx, meme, "shitpost.png")

    @commands.command()
    async def audioimage(self, ctx, *, url=None):
        """Turn an image into audio."""

        result = await self.process_file(ctx, url)
        if result is None:
            return

        im = Image.open(result.data).convert("L")
        im.thumbnail((200, 200))
        buffer = BytesIO()
        arr = numpy.array(im, dtype=numpy.int8)
        new = []
        for i in range(arr.shape[1]):
            try:
                new.extend(list(arr[i]))
            except IndexError:
                break
                # in theory this /should/ be fine, but there's some strangeness with PIL / numpy / my code
                # that breaks the last item if the file is of a certain type, not sure why
                # shit's wack yo

        to_write = numpy.array(new, dtype=numpy.int8)
        wavfile.write(buffer, 10000, to_write)
        constructed_file = discord.File(fp=buffer, filename="audioimage.wav")

        await ctx.send(file=constructed_file)

    @commands.command()
    async def wheelofban(self, ctx):
        """Spin the wheel of ban!"""

        banhandler = BanConglomerate()
        wheel = Image.open(f"{ROOT_DIRECTORY}extensions/data/wheel_of_ban.png")
        wheel = wheel.convert("RGBA").resize((512, 512), Image.ANTIALIAS)
        ban = Image.open(f"{ROOT_DIRECTORY}extensions/data/ban_spin_top.png")
        ban = ban.convert("RGBA").resize((512, 512), Image.ANTIALIAS)
        ban_mask = Image.open(f"{ROOT_DIRECTORY}extensions/data/transparent_ban.png").convert("RGBA")
        degrees, to_spin, = 0, 9.9
        frames = []  # what could possibly go wrong

        for _ in range(random.randint(25, 170)):
            degrees += to_spin
            frames.append(await self.wrap(self.package_wheel, wheel, degrees, ban, ban_mask, banhandler))

        for _ in range(70):
            to_spin = to_spin * 0.95
            degrees += to_spin
            frames.append(await self.wrap(self.package_wheel, wheel, degrees, ban, ban_mask, banhandler))

        for _ in range(20):
            frames.append(await self.wrap(self.package_wheel, wheel, degrees, ban, ban_mask, banhandler))

        await self.save_and_send(
            ctx, frames[0], "wheelofban.gif", save_all=True,
            append_images=frames[1:], optimize=True, loop=0, duration=30
        )

    @commands.command()
    async def imagescript(self, ctx, *, url_and_code):
        """Runs code for Lobstero's Imagescript scripting language.
        At the moment, this is very poorly documented and still a WIP. It will be expanded upon later."""

        url = None
        code = url_and_code
        image = None

        if " " in url_and_code:
            split = url_and_code.split()
            if ";" not in split[0]:
                url = split[0]
                code = " ".join(split[1:])

        try:
            image = await self.process_file(ctx, url)
        except (commands.BadArgument, IndexError):  # conversion failed
            code = url_and_code
            await ctx.simple_embed(f"No images matching \"{url}\" were found.")

        if image is None:
            return

        cleaned = codeblock_converter(code)

        try:
            await self.imagescript_run(ctx, cleaned.content, image)
        except ImageScriptException as e:
            embed = discord.Embed(color=16202876, title="Something went wrong")
            embed.description = f"```{type(e).__name__}: {e.args[0]}```\n"
            if len(e.args) > 1:  # TODO: not this
                embed.description += f"This happened during line/ operation {e.args[1]}.\n"

            embed.description += inspect.getdoc(e)
            await ctx.send(embed=embed)

    # This is an abstract function intended to be passed to a specifically configured Command
    # It is used to efficiently wrap around process_single for many commands
    async def abstract_process_single(self, ctx, *, url=None):
        """You shouldn't see this!"""
        await self.process_single(ctx.command.name, ctx, url)

    # Create the commands from the abstraction and add relevant information
    for command_name, command_docstring in DOCSTRING_MAPPING.items():
        c = commands.Command(vars()["abstract_process_single"], name=command_name, help=command_docstring)
        vars()[f"{command_name}_command"] = c

    # This local will cause two of the same commands to be registered if we keep it around
    del c


def setup(bot: commands.Bot):
    bot.add_cog(Cog(bot))
