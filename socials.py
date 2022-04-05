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

def run_inkscape(input: str, output: str):
    click.echo(f"Running inkscape to produce {output}")
    subprocess.run(['inkscape', '--export-type=png', f'--export-filename={output}', input])


class DigitalMeetup(BaseModel):
    class Meta(BaseModel):
        template: str

    class Instance(BaseModel):
        year: str
        date: str
        time: str

    meta: Meta
    instances: List[Instance]

class Posters(BaseModel):
    digital_meetup: DigitalMeetup


class Output(BaseModel):
    title: str
    path: str


def handle_digital_meetup(digital_meetup: DigitalMeetup) -> List[Output]:
    with open(digital_meetup.meta.template, 'r') as reader:
        template = reader.read()

    outputs = []

    for instance in digital_meetup.instances:
        with tempfile.NamedTemporaryFile(suffix=".svg") as fp:
            rendered = chevron.render(
                template=template,
                data=instance
            )
            parent_dir = f"./build/{instance.year}/digital-meetup/"
            Path(parent_dir).mkdir(parents=True, exist_ok=True)

            fp.write(rendered.encode('utf-8'))

            output_filename = f"{parent_dir}digital-meetup-{instance.year}-{instance.date}-{instance.time}.png"
            run_inkscape(fp.name, output_filename)

            outputs.append(Output(
                title=f"Digital Meetup ({instance.year}) {instance.date} @ {instance.time}",
                path=output_filename.lstrip("./build")
            ))

    return outputs

@click.command()
def socials():
    """Generates social content"""
    click.echo("Generating socials content...")

    with open('posters.toml', 'r') as reader:
        posters_toml_string = reader.read()

    posters_toml = toml.loads(posters_toml_string)

    posters = Posters(**posters_toml)

    outputs = [
        *handle_digital_meetup(posters.digital_meetup)
    ]

    template = Template("""
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
    """).render(outputs=outputs)

    Path("./build/index.html").write_text(template)
    Path("./build/posters.json").write_text(posters.json(indent=2))
    shutil.copytree("./templates", "./build/templates", dirs_exist_ok=True)

    click.echo("Generating social content")

if __name__ == '__main__':
    socials()
