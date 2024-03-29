from pathlib import Path
import shutil
from typing import List
import subprocess
import tempfile

import chevron
import click
import toml
from pydantic import BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape
from jinja2 import Template


def produce_png(input: str, output: str):
    click.echo(f"Producing {output}...")
    subprocess.run(["rsvg-convert", input, "-o", output])
    click.echo(f"Produced {output}!")


class Meetup(BaseModel):
    class Meta(BaseModel):
        template: str

    class Instance(BaseModel):
        year: str
        date: str
        time: str

    meta: Meta
    instances: List[Instance]


class Posters(BaseModel):
    digital_meetup: Meetup
    element_meetup: Meetup
    qeii_meetup: Meetup
    jumping_bean_meetup: Meetup


class Output(BaseModel):
    title: str
    path: str


def handle_meetup(prefix: str, meetup: Meetup) -> List[Output]:
    with open(meetup.meta.template, "r") as reader:
        template = reader.read()

    outputs = []

    for instance in meetup.instances:
        with tempfile.NamedTemporaryFile(suffix=".svg") as fp:
            rendered = chevron.render(template=template, data=instance)
            parent_dir = f"./build/{instance.year}/{prefix}/"
            Path(parent_dir).mkdir(parents=True, exist_ok=True)

            fp.write(rendered.encode("utf-8"))

            output_filename = f"{parent_dir}{prefix}-{instance.year}-{instance.date}-{instance.time}.png"
            produce_png(fp.name, output_filename)

            outputs.append(
                Output(
                    title=f"{prefix} ({instance.year}) {instance.date} @ {instance.time}",
                    path=f"./{output_filename.lstrip('./build')}",
                )
            )

    return outputs


@click.command()
def socials():
    """Generates social content"""
    click.echo("Generating socials content...")

    with open("posters.toml", "r") as reader:
        posters_toml_string = reader.read()

    posters_toml = toml.loads(posters_toml_string)

    posters = Posters(**posters_toml)

    outputs = [
        *handle_meetup("digital-meetup", posters.digital_meetup),
        *handle_meetup("element-meetup", posters.element_meetup),
        *handle_meetup("qeii-meetup", posters.qeii_meetup),
        *handle_meetup("jumping-bean-meetup", posters.jumping_bean_meetup)
    ]

    outputs.reverse()

    template = Template(
        """
<!DOCTYPE html>
<html>
<head>
    <title>CTSNL Socials</title>
    <style>
body {
    font-family: sans-serif;
    margin: 4rem;
}
.output {
    margin: 2rem 0;
}
.output img {
    max-width: 40rem;
}
    </style>
<head>
<body>
    <h1>CTSNL Socials</h1>
    <p>Automagically generating social assets</p>
    <a href="https://github.com/CTS-NL/Socials">https://github.com/CTS-NL/Socials</a>
    {% for output in outputs %}
    <div class="output">
        <h2>{{ output.title }}</h2>
        <img src="{{ output.path }}" />
    </div>
    {% endfor %}
</body>
</html>
    """
    ).render(outputs=outputs)

    Path("./build/index.html").write_text(template)
    Path("./build/posters.json").write_text(posters.json(indent=2))
    shutil.copytree("./templates", "./build/templates", dirs_exist_ok=True)

    click.echo("Generating social content")


if __name__ == "__main__":
    socials()
