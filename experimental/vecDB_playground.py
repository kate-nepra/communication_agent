import weaviate
import json


def create_article_schema(client):
    client.schema.delete_class("Article")

    article_class = {
        "class": "Article",
        "properties": [
            {
                "name": "title",
                "dataType": ["string"]
            },
            {
                "name": "text",
                "dataType": ["text"]
            },
            {
                "name": "url",
                "dataType": ["string"]
            },
            {
                "name": "dateFetched",
                "dataType": ["date"]
            }

        ]
    }

    client.schema.create_class(article_class)


def import_data(client, data, class_name):
    """
    Imports data to Weaviate
    :param client: weaviate client
    :param data: data to import
    :param class_name: class name
    :return: None
    """
    # Prepare a batch process
    client.batch.configure(batch_size=100)  # Configure batch
    with client.batch as batch:
        # Batch import all Questions
        for i, d in enumerate(data):
            properties = {"title": d["title"],
                          "text": d["text"],
                          "url": d["url"],
                          "dateFetched": d["dateFetched"]
                          }
            batch.add_data_object(properties, class_name)


client = weaviate.Client("http://localhost:8080")  # Replace "localhost:8080" with your Weaviate URL

test_data = [{"title": "Biology",
              "text": "Biology is the scientific study of life. It is a natural science with a broad scope but has several unifying themes that tie it together as a single, coherent field.[1][2][3] For instance, all organisms are made up of cells that process hereditary information encoded in genes, which can be transmitted to future generations. Another major theme is evolution, which explains the unity and diversity of life.[1][2][3] Energy processing is also important to life as it allows organisms to move, grow, and reproduce. Finally, all organisms are able to regulate their own internal environments. Biologists are able to study life at multiple levels of organization,[1] from the molecular biology of a cell to the anatomy and physiology of plants and animals, and evolution of populations.[1][6] Hence, there are multiple subdisciplines within biology, each defined by the nature of their research questions and the tools that they use.[7][8][9] Like other scientists, biologists use the scientific method to make observations, pose questions, generate hypotheses, perform experiments, and form conclusions about the world around them. Life on Earth, which emerged more than 3.7 billion years ago,[10] is immensely diverse. Biologists have sought to study and classify the various forms of life, from prokaryotic organisms such as archaea and bacteria to eukaryotic organisms such as protists, fungi, plants, and animals. These various organisms contribute to the biodiversity of an ecosystem, where they play specialized roles in the cycling of nutrients and energy through their biophysical environment.",
              "url": "https://www.cookieexample.com",
              "dateFetched": "2023-08-01T00:00:00Z"
              },
             {"title": "Chocolate Chip Cookie",
              "text": "Everyone needs a classic chocolate chip cookie recipe in their repertoire, and this is mine. It is seriously the Best Chocolate Chip Cookie Recipe Ever! I have been making these for many, many years and everyone who tries them agrees they’re out-of-this-world delicious! Plus, there’s no funny ingredients, no chilling, etc. Just a simple, straightforward, amazingly delicious, doughy yet still fully cooked, chocolate chip cookie that turns out perfectly every single time! These are everything a chocolate chip cookie should be. Crispy and chewy. Doughy yet fully baked. Perfectly buttery and sweet.",
              "url": "https://www.cookieexample.com",
              "dateFetched": "2023-08-01T00:00:00Z"
              },
             {"title": "Article about Brno",
              "text": "Brno is a city in the South Moravian Region of the Czech Republic. Located at the confluence of the Svitava and Svratka rivers, Brno has about 390,000 inhabitants, making it the second-largest city in the Czech Republic after the capital, Prague, and one of the 100 largest cities of the EU. The Brno metropolitan area has almost 700,000 inhabitants.",
              "url": "https://www.brnoexample.com",
              "dateFetched": "2022-03-01T00:00:00Z"
              },
             {"title": "Brno University of Technology",
              "text": "Brno University of Technology is a university located in Brno, Czech Republic. Being founded in 1899 and initially offering a single course in civil engineering, it grew to become a major technical Czech university with over 18,000 students enrolled at 8 faculties and 2 university institutes.",
              "url": "https://www.uniexample.com",
              "dateFetched": "2023-01-05T00:00:00Z"
              }
             ]

create_article_schema(client)
import_data(client, test_data, "Article")
nearText = {"concepts": ["baking"], }

result = (
    client.query
    .get("Article", ["title", "text", "url", "dateFetched"])
    .with_near_text(nearText)
    .with_additional(['certainty'])
    .do())

print(json.dumps(result, indent=4))
