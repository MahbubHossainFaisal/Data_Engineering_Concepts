import matplotlib.pyplot as plt
import seaborn as sns

def plot_bar_chart(data,x_column,y_column,title=None,x_label=None,y_label=None,color='red',save_path=None):
    plt.figure(figsize=(10,6))
    sns.barplot(x=x_column,y=y_column,data=data,color=color)
    if title:
        plt.title = title
    if x_label:
        plt.x_label = x_label
    if y_label:
        plt.y_label = y_label
    if save_path:
        plt.savefig(save_path)
    
    plt.show()

def plot_line_chart(data,x_column,y_column,title=None,x_label=None,y_label=None,color='red',save_path=None):
    plt.figure(figsize=(10,6))
    sns.barplot(data[x_column],data[y_column],color=color)
    if title:
        plt.title = title
    if x_label:
        plt.x_label = x_label
    if y_label:
        plt.y_label = y_label
    if save_path:
        plt.savefig(save_path)
    
    plt.show()

